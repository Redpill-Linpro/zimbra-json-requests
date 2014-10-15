Install
=======

pip install requests or pip install -r ./requirements.txt


Why
===
Why use this, minimal, library rather than the much more complete `python-zimbra`_ package?

No reason really. First of all the libraries were developed around the same time but theres no overlap between the libraries. Still, the same aproach, more or less, are used in both.

The main reason I didn't drop my effort when I realized there was a high-quality python-zimbra project was that I couldn't get batch requests to work - and there was no easy fix that would be general enough to adhere to python-zimbras standards. Also, having the classes pre-defined with strong parameter setting is very beneficial to us since it becomes **much** easier to understand what's going on. 



Overview
--------
- both libraries does authentication
- both libraries does batch requests.. mostly
- zimbra_json_requests is a simpler one-file library.
- zimbra_json_requests has done the mapping for many of the most used Zimbra commands, ie. you might not need to read, understand and translate the the Zimbra SOAP documentation to get started.
- zimbra_json_requests can act the same way as python-zimbra if the method you need is not mapped to a coresponding json method.
- python-zimbra also deals with XML
- python-zimbra treats responses as a object


.. _python-zimbra: https://github.com/Zimbra-Community/python-zimbra


Examples
--------

.. code-block:: python

	>>> from zimbra_json_requests import ZimbraJSONRequest, ZimbraAuthRequest, AuthRequest, GetFolderRequest, Contact, CreateContactRequest
	>>> from zimbra_json_requests import get_auth_token
	>>>
	>>>
	>>> user_token, u_uid = get_auth_token('some@one.com', <pre-auth key>, admin=False)
	>>> admin_token, a_uid = get_auth_token('admin@one.com', <password>, admin=True)
	>>> 
	>>> # get a users folder
	>>> _user_folder = ZimbraJSONRequest(admin_token, user_address)
	>>> _user_folder.Body = GetFolderRequest()
	>>> _res = _user_folder.request()
	>>> _folder = (json.loads(_res.content))["Body"]["GetFolderResponse"]["folder"]
	>>>
	>>> # create some contacts in a batch request.
	>>> c1 = Contact()
	>>> c1.firstName = "Kalle"
	>>> c1.lastName = "Kanin"
	>>> 
	>>> c2 = Contact()
	>>> c2.firstName = "Pelle"
	>>> c2.lastName = "Parafin"
	>>> 
	>>> cr = CreateContactRequest()
	>>> cr.contact = c1
	>>> cr.contact = c2
	>>> tp = cr._serialize()
	>>>
	>>> ccr = ZimbraJSONRequest(admin_token, a_uid)
	>>> ccr.Body = cr
	>>> ccr.requests()
	>>> ...