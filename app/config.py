from typing import Dict
from Configs import ConfigBase


class DEFAULT(ConfigBase):

    NEO4J_ADMIN_QA: Dict = {}
    """
    NEO4J - dict - Connection details for you Neo4j database. For possible keys refer to the [py2neo](https://py2neo.org) doc @ https://py2neo.org/2021.1/profiles.html#individual-settings
	example: 
	`{"host":"localhost",password:"mypw", port:7688}`
    """

    NEO4J_PUBLIC_PROD: Dict = {}
    """
    NEO4J - dict - Connection details for you Neo4j database. For possible keys refer to the [py2neo](https://py2neo.org) doc @ https://py2neo.org/2021.1/profiles.html#individual-settings
	example: 
	`{"host":"localhost",password:"mypw", port:7688}`
    """

    API_ORIGIN: str = None
    """
    API_ORIGIN - str -  Tell the server on which origin is will server its API.
	The API server needs to know its origin to configure CORS correctly.
	example:
	`https://myapi.mydomain.com:443`
    """

    LOG_LEVEL: str = "INFO"
    """
    LOG_LEVEL - str - Loglevel as in https://docs.python.org/3/library/logging.html#levels
    """

    UVICORN_WEBSERVER_PARAMS: Dict = {
        "port": 8000,
        "host": "0.0.0.0",
    }
    """
    UVICORN_WEBSERVER_PARAMS - dict - https://www.uvicorn.org/#uvicornrun
    """
