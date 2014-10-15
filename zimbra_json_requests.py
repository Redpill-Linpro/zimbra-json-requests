#! /usr/bin/env python
# -*- coding: utf-8 -*-

import abc
import json
import requests
import cPickle
import hashlib
from datetime import datetime
import hmac
import logging
import logging.config
import settings

__author__ = "Rune Hansen"
__copyright__ = "Copyright 2013, Redpill Linpro AS"
__credits__ = []
__license__ = "GPLv3"
__version__ = "1.2"

logging.config.dictConfig(settings.LOG_SETTINGS)
logger = logging.getLogger("File")


class iZimbra(object):
    """Highest level interface"""
    __meta__ = abc.ABCMeta

    @abc.abstractmethod
    def _serialize(self):
        """Serialize to dict"""

class iZimbraJSONRequest(object):
    """Interface class for ZimbraJSONRequests"""
    __meta__ = iZimbra

    @abc.abstractproperty
    def Body(self):
        return

    @Body.setter
    def Body(self, value):
        return

    @abc.abstractmethod
    def request(self):
        return

class ValidationError(Exception):
    def __init__(self, message):
        super(ValidationError, self).__init__(self, message)

class Dummy(iZimbra):
    def _serialize(self):
        return {}
    
class ZimbraJSONRequest(iZimbraJSONRequest):
    """Mother for all zimbra requests"""
    def __init__(self, auth, uid):
        """
        Keyword arguments:
        auth -- the authentication token
        uid  -- the user ident belonging to the auth token
        """
        self._Body = Dummy()
        self.auth = auth
        self.uid = uid
        super(ZimbraJSONRequest, self).__init__()

    def clean(self):
        self._Body = Dummy()

    @property
    def Body(self):
        return self._Body

    @Body.setter
    def Body(self, value):
        self._Body = value

    def _serialize(self):
        return {"Header":
                {"context":
                 {"_jsns":"urn:zimbra",
                  "format":{"type":"js"},
                  "userAgent":{"name":"zclient","version":"8.0.6_GA_5922"},
                  "account":{"_content":self.uid,"by":"name"},
                  "authToken":self.auth}
                 },
                "Body":self.Body._serialize()}

    def request(self):
        _payload = json.dumps(self._serialize())
        _req = requests.post(settings.ZIMBRA_ADMIN_URL+self.Body.__class__.__name__,
                             data=_payload, verify=False)
        return _req

##
# Auth methods

def compute_preauth(account, preauthkey, by='name', expires=0, timestamp=None):
    """Based on ruby example code found on zimbra proper
    Keyword arguments:
    account    -- the user ident
    preauthkey -- the servers preauth key
    by         -- default by 'name'
    expires    -- set to 0 (not in use)
    timestamp  -- now in seconds * 1000

    NOTE:
    - PREAUTH can only be used on non-admin accounts.
    - PREAUTH namespace is zimbraAccount
    - SOAP URI can be /service/soap or /service/admin/soap/ - this does not seem to matter
    - You need a password to authenticate an ADMIN user with SOAP.
    - Rumor has it that it's possible to use PREAUTH to authenticate an ADMIN user via REST (/preauth?)
    """

    pkey = hmac.new(preauthkey,'{}|{}|{}|{}'.format(
        account, by, expires, timestamp), hashlib.sha1).hexdigest()

    return pkey

class ZimbraAuthRequest(ZimbraJSONRequest):
    def __init__(self):
        pass

    def _serialize(self):
        return {"Header":
                {"context": {"_jsns": "urn:zimbra",
                             "format": {"type": "js"}
                             }
                 },"Body":self.Body._serialize()}

class AuthRequest(object):
    """
    The auth process is not optimal. Use the helper function: get_auth_token
    for a more pleasant experience.
    (Why did it become this way..? Didn't think. Period.
    That, and I wanted the API to be as close to ZibraJSONRequest as possible.
    No excuse tho.)
    """
    def __init__(self, uid, pkey, admin=False):
        """
        Keyword arguments:
        uid   -- The user id
        pkey  -- preauth generated key or password
        admin -- False or True
        
        Returns a authentication token and the user ID used to generate the authentication token.
        """
        self.uid = uid
        self.pkey = pkey
        self.admin = admin
        super(AuthRequest, self).__init__()

    def _serialize(self):
        if self.admin:
            return {self.__class__.__name__:
                    {"account":
                     {"by": "name", "_content": self.uid},
                     "password": self.pkey,
                     "_jsns": "urn:zimbraAdmin"
                     }
                    }
        else:
            timestamp = int(datetime.now().strftime("%s")) * 1000
            _pkey = compute_preauth(self.uid, self.pkey, "name", 0, timestamp)
            return {self.__class__.__name__:
                    {"account":{"by": "name", "_content":self.uid},
                     "preauth":{"timestamp": timestamp, "expires": 0, "_content": _pkey},
                     "_jsns":"urn:zimbraAccount"}
                    }
#
##

class GetFolderRequest(object):
    """Returns all information about the requesters folder"""
    def _serialize(self):
        return {self.__class__.__name__:{"_jsns":"urn:zimbraMail"}}

class GetInfoRequest(object):
    """Returns everything but the kitchen sink
    Basically, useless information.
    """
    def _serialize(self):
        return {self.__class__.__name__:{"_jsns":"urn:zimbraAccount",
                                         "sections":"mbox,prefs,attrs,props,idents,sigs,dsrcs,children",
                                         "rights":""}
                }

class GetAccountInfoRequest(object):
    """Useful for admins to get information about a user"""
    def __init__(self, uid):
        """
        Keyword arguments:
        uid -- the user id
        """
        self.uid = uid
        super(GetAccountInfoRequest,self).__init__()

    def _serialize(self):
        return {self.__class__.__name__:
                {"_jsns":"urn:zimbraAccount",
                 "account":{"by":"name","_content":self.uid}}}

class CreateContactRequest(object):
    """This class creates one or more contacts in the users
    default contact list"""
    def __init__(self):
        self._contact = []
        super(CreateContactRequest,self).__init__()

    def add_to_batch(self, contact):
        self._contact.append(contact)

    @property
    def contact(self):
        return self._contact

    @contact.setter
    def contact(self, contact):
        self.add_to_batch(contact)

    def _serialize(self):
        _header = {"BatchRequest":{
            "_jsns":"urn:zimbra",
            "onerror":"continue",
            self.__class__.__name__:{}}}


        _tmp_body = []
        for i, item in enumerate(self.contact):
            _tmp_body.append({"_jsns":"urn:zimbraMail",
                              "cn":{"a":item._serialize()},
                              "requestId":i})

        _header['BatchRequest'][self.__class__.__name__] = _tmp_body

        return _header

class Contact(object):
    """Container class for attributes on a Contact.
    The Contact it self is used as input to CreateContactRequest.contact

    Attributes:
      firstName
      lastName
      email
      mobilePhone
      company
      ...arbitrary verbs

    Uses the build in __dict__ to populate a dict in the correct zimbra format
    """
    def _serialize(self):
        return [{'n':k[0],'_content':k[1]} for k in self.__dict__.items()]

class SearchRequest(object):
    """Same as using the search field in zimbra, but limited to accounts.
    The limit is artificial, but is easy to remedy w/o side effects if
    anyone sees the need."""

    def __init__(self, offset=0, limit=100, query=None):
        """
        Keyword arguments:
        offset -- start offset
        limit  -- start limit
        query  -- what to search for
        """
        self.offset = offset
        self.limit = limit
        self.query="in:accounts"
        if query:
            self.query += " AND " + query

    def _serialize(self):
        return {self.__class__.__name__:{"_jsns":"urn:zimbraMail",
                                         "sortBy":"nameAsc","tz":{"id":"Europe/Berlin"},
                                         "locale":{"_content":"en_US"},
                                         "offset":self.offset,"limit":self.limit,"query":self.query,
                                         "types":"contact"}}
class ContactActionRequest(object):
    """Work on a users contacts"""
    def __init__(self, cid, action="delete"):
        """
        Keyword arguments:
        cid -- the users zimbra id
        action -- one of [delete|update]
        """
        self.cid = cid
        self.action = action
        self._contact = None

    @property
    def contact(self):
        return self._contact

    @contact.setter
    def contact(self, contact):
        self._contact = contact

    def _serialize(self):
        res = {self.__class__.__name__:{
            "_jsns":"urn:zimbraMail",
            "action":{
                "op": {
                    "_content":self.action
                    },
                "id": {
                    "_content": self.cid
                    },
                "a": None}}
               }
        if self.action == "update" and self.contact is not None:
            res[self.__class__.__name__]['a'] = self.contact._serialize()
        elif self.action == "delete":
            res[self.__class__.__name__]['action'].pop('a')
        return res

class ModifyContactRequest(object):
    """Modify the contact in place"""
    def __init__(self, cid):
        """
        Keyword arguments:
        cid -- the zimbra id
        """
        self.cid = cid
        self._contact = None

    @property
    def contact(self):
        return self._contact

    @contact.setter
    def contact(self, contact):
        self._contact = contact

    def _serialize(self):
        res = {self.__class__.__name__:{
            "_jsns":"urn:zimbraMail","replace":"0","force":"1",
                                    "cn":{"id":self.cid,
                                          "a":self.contact._serialize()}}}
        return res

class DistributionList(object):
    """""Container class for attributes on a DistributionList.
    The Contact it self is used as input to Create DistributionListRequest

    Attributes:
    uid                   -- immutable
    mail                  -- immutable
    cn                    -- in use
    displayName           -- in use
    zimbraMailStatus      -- not used
    zimbraMailHost        -- not used
    zimbraId              -- not used
    zimbraCreateTimestamp -- not used
    objectClass           -- not used
    zimbraMailAlias       -- not used
    ...arbitrary verbs

    Uses the build in __dict__ to populate a dict in the correct zimbra format

    """
    def _serialize(self):
        return [{'n':k[0],'_content':k[1]} for k in self.__dict__.items()]

class CreateDistributionListRequest(object):
    """Creates a distribution list"""
    def __init__(self, name):
        """
        Keyword arguments:
        name -- the name of the list
        """
        self.name = name
        self._distlist = None

    @property
    def distributionlist(self):
        return self._distlist

    @distributionlist.setter
    def distributionlist(self, distlist):
        self._distlist = distlist

    def _serialize(self):
        return {self.__class__.__name__:{"_jsns":"urn:zimbraAdmin",
                                         "name":self.name,
                                         "a":self.distributionlist._serialize()}
                                         }


class DistributionListActionRequest(object):
    """Work on distribution lists
    (In the official documentation, this method is documented using a different namespace)"""
    _implemented_commands = ["delete", "modify", "addMembers", "removeMembers"]

    def __init__(self, action, zimbraId):
        """
        Keyword arguments:
        action   --  one of [ delete | modify | addMembers | remove ]
        zimbraId -- zimbraid
        """
        if action in self._implemented_commands:
            self.action = action
        else:
            raise ValidationError("Command {} not in Implemented Commands".format(action))
        self.zimbraId = zimbraId
        self._distributionlistmembers = []
        self._distlist = None

    def add_to_seq(self, member):
        """
        helper method to add an item to the sequence
        """
        self._distributionlistmembers.append(member)

    @property
    def distributionlist(self):
        return self._distlist

    @distributionlist.setter
    def distributionlist(self, distlist):
        self._distlist = distlist

    @property
    def member(self):
        return self._distributionlistmembers

    @member.setter
    def member(self, member):
        """This method ensures correct JSON compatible formatting of data.
        It also contains a rather rudimentary check to see if member is a
        valid formattet email address."""
        def checkvalidemail(member):
            if (not "@" in member) or (not "." in member.split("@")[1]):
                raise ValidationError("Member must be a valid email address")
            return member

        if isinstance(member, list):
            for m in member:
                try:
                    self.add_to_seq({"_content":checkvalidemail(m.encode("utf-8"))})
                except UnicodeDecodeError as e:
                    logger.error(u"Email address failed {} : {}".format(m, e))
        else:
            self.add_to_seq({"_content":checkvalidemail(member)})

    def _serialize(self):
        """DistributionListActionRequest can seem a bit complex.
        Thus, we provide an example

        Example:
        d = DistributionListActionRequest("modify", "zyx...123")
        dl = DistributionList()
        dl.displayName = "Some display name"
        d.distributionlist = dl
        
        (res dict defaults to "delete" action since this action does
        not need to modify the dict.)

        """
        res = {self.__class__.__name__:{
            "_jsns":"urn:zimbraAccount",
            "dl":{"_content":self.zimbraId, "by":"id"},
            "action": {
                "op": {
                    "_content":self.action
                    }

            }}
               }

        if self.action == "modify":
            res[self.__class__.__name__]["action"]["a"] = self.distributionlist._serialize()

        if self.action in ["addMembers", "removeMembers"] and self.member:
            res[self.__class__.__name__]["action"]["dlm"] = self.member

        return res




class AddDistributionListMemberRequest(object):
    """This method is completly undocumented by Zimbra proper. 
    Use with care!"""
    def __init__(self, zimbraId):
        """
        Keyword arguments:
        zimbraId -- the zimbra ID
        """
        self.zimbraId = zimbraId
        self._distributionlistmembers = []

    def add_to_seq(self, member):
        self._distributionlistmembers.append(member)

    @property
    def member(self):
        return self._distributionlistmembers

    @member.setter
    def member(self, member):
        if (not "@" in member) or (not "." in member.split("@")[1]):
                    raise ValidationError("Member must be a valid email address")
        self.add_to_seq({"_content":member})

    def _serialize(self):
        return {self.__class__.__name__:{"_jsns":"urn:zimbraAdmin",
                                         "id":self.zimbraId,
                                         "dlm":self.member,
                                         }
                }


class GetShareInfoRequest(object):
    """Returns information about a share by name"""
    def __init__(self, name):
        self.name = name

    def _serialize(self):
        return {self.__class__.__name__:{"_jsns":"urn:zimbraAccount",
                                         "owner":{"by":"name","_content":self.name}
                                         }
                }

class GetDistributionListRequest(object):
    """Returns the content of a Distribution list by name"""
    def __init__(self, dl_name, offset=0, limit=100):
        """
        Keyword arguments:
        dl_name -- the name of the distribution list
        offset  -- the start offset
        limit   -- the start limit
        """
        self.dl_name = dl_name
        self.offset = offset
        self.limit = limit

    def _serialize(self):
        return {self.__class__.__name__:{"_jsns":"urn:zimbraAdmin",
                                         "offset":self.offset,
                                         "limit":self.limit,
                                         "dl":{"_content":self.dl_name,"by":"name"}}}

class CreateMountpointRequest(object):
    """Creates a named mount for the given zimbra id"""
    def __init__(self, display_name, zimbra_id, rid, color):
        """
        Keyword arguments:
        display_name -- the mount name
        zimbra_id    -- the id of the account where the mount shuld be created
        rid          -- the id of the shared item
        color        -- one of [1|2|...|9|...]
        """
        self.display_name = display_name
        self.zimbra_id = zimbra_id
        self.rid = rid
        self.color = color

    def _serialize(self):
        return {self.__class__.__name__:{"_jsns":"urn:zimbraMail",
                                         "link":{"name":u"{}'s Calendar".format(self.display_name),
                                                 "zid":self.zimbra_id,
                                                 "rid":self.rid,
                                                 "color":self.color,
                                                 "l":"1",
                                                 "f":"#"}
                                         }
                }

class SearchDirectoryRequest(object):
    def __init__(self, offset=0, limit=100, query="", qtype="resources"):
        """Set up a search for non system accounts only
        Keyword arguments:
        query -- ldap string. Examples: (sn=Doe) | (uid=johndoe) | ...
        qtype -- one of [resources | accounts | aliases | ...]
        """
        self.offset = offset
        self.limit = limit
        self.qtype = qtype
        self.query = "(&(!(zimbraIsSystemAccount=TRUE)){})".format(query)

    def _serialize(self):
        return {self.__class__.__name__:{"_jsns":"urn:zimbraAdmin",
                                         "sortBy":"name",
                                         "tz":{"id":"Europe/Berlin"},
                                         "locale":{"_content":"en_US"},
                                         "offset":self.offset,
                                         "limit":self.limit,
                                         "attrs":"displayName,zimbraId,zimbraAliasTargetId,cn,sn,zimbraMailHost,uid,zimbraCOSId,zimbraAccountStatus,zimbraLastLogonTimestamp,description,zimbraIsSystemAccount,zimbraIsDelegatedAdminAccount,zimbraIsAdminAccount,zimbraIsSystemResource,zimbraAuthTokenValidityValue,zimbraIsExternalVirtualAccount,zimbraMailStatus,zimbraIsAdminGroup,zimbraCalResType,zimbraDomainType,zimbraDomainName,zimbraDomainStatus",
                                         "query":self.query,
                                         "types":self.qtype}}


##
# Helper functions
##

def get_auth_token(uid, pkey, admin=False):
    """Helper function for easy authentication.
    
    Returns the authentication token and the uid used to generate it
    Keyword arguments:
    uid   -- the user id
    pkey  -- pre auth key or password
    admin -- False or True
    """
    _za = ZimbraAuthRequest()
    _za.Body = AuthRequest(uid, pkey, admin)
    _res = _za.request()
    _authToken = json.loads(_res.content)["Body"]["AuthResponse"]["authToken"][0]["_content"]
    return (_authToken, uid)

def get_all_zimbra_contacts(auth, uid, offset=0, limit=100, cache=None):
    """Returns all contacts on a given account
    
    Keyword arguments:
    auth   -- the auth token
    uid    -- the uid
    offset -- start offset
    limit  -- start limit
    cache  -- initial None
    """
    if cache is None:
        cache = []
    _search = ZimbraJSONRequest(auth, uid)
    _search.Body = SearchRequest(offset=offset, limit=limit)
    _result = _search.request()
    _dict_results = json.loads(_result.content)
    cache.append(_dict_results)
    if _dict_results['Body']['SearchResponse']['more']:
        return get_all_zimbra_contacts(auth, uid, offset=offset+limit, limit=limit, cache=cache)
    return cache

def get_all_admin_resources(auth, uid, offset=0, limit=50, query="", qtype=None, cache=None):
    """Returns all named resources for the Admin user

    Keyword arguments:
    auth   -- the admin auth token
    uid    -- the admin uid
    offset -- start offset
    limit  -- start limit
    query  -- ldap query formated string ie. '(sn=<something>)'
    qtype  -- one of [resources | accounts | aliases | ...]
    cache  -- initial None    
    """
    if cache is None:
        cache = []
    _search = ZimbraJSONRequest(auth, uid)
    _search.Body = SearchDirectoryRequest(offset=offset, limit=limit, query=query, qtype=qtype)
    _result = _search.request()
    _dict_results = json.loads(_result.content)
    cache.append(_dict_results)
    if _dict_results['Body']['SearchDirectoryResponse']['more']:
        return get_all_admin_resources(auth, uid, offset=offset+limit, limit=limit, query=query, qtype=qtype, cache=cache)
    return cache

def get_all_distributionlist_members(auth, uid, dl_name, offset=0, limit=100, cache=None):
    """Returns all the members on a distribution list. Some additional processing is done
    to ensure the return of a uniqe set of email addresses.
    
    Keyword arguments:
    auth    -- the admin auth token
    uid     -- the admin uid
    dl_name -- the distribution list name
    offset  -- start offset
    limit   -- start limit
    cache   -- initial None    
    """
    if cache is None:
        cache = set()
    _search = ZimbraJSONRequest(auth, uid)
    _search.Body = GetDistributionListRequest(dl_name, offset, limit)
    _dict_results = json.loads(_search.request().content)
    try:
        cache.update([x["_content"] for x in _dict_results["Body"]["GetDistributionListResponse"]["dl"][0]["dlm"]])
        if _dict_results["Body"]["GetDistributionListResponse"]["more"]:
            return get_all_distributionlist_members(auth, uid, dl_name, offset=offset+limit, limit=limit, cache=cache)
    except KeyError as e:
        raise KeyError(e)
    return list(cache)

def delete_all_zimbra_contacts(auth, uid, offset=0, limit=100):
    """Removes all the contacts from an account

    Keyword arguments:
    auth   -- the authentication token
    uid    -- the uid of the account
    offset -- the initial offset
    limit  -- the initial limit
    cache  -- initial None
    """
    cache  = get_all_zimbra_contacts(auth, uid, offset=0, limit=100, cache=None)
    _t = []
    try:
        for item in cache:
            for contact in item['Body']['SearchResponse']['cn']:
                _t.append(contact.get('id'))

        _delete = ZimbraJSONRequest(auth, uid)
        _delete.Body = ContactActionRequest(",".join(set(_t)),action="delete")
        _result = _delete.request()
        return _result.status_code
    except KeyError as e:
        logger.warning("{0} : Error".format(str(e)))
    finally:
        del cache
    return

def md5_hash_zimbra_contact(zimbra_contact):
    """Utility method for storing hashed versions of a contact."""
    return hashlib.md5(cPickle.dumps(zimbra_contact)).hexdigest()


