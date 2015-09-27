# Herqles Manager

The Manager is the task routing, security and management component of the Herqles system.

# Version 2.0

This version is a complete rewrite and is not compatible with older versions. 
Please use caution when upgrading.

## Requirements

* A SQL Server
    * The specific python driver needs to be installed manually
* RabbitMQ Server(s)
* LDAP Server and developer tools
    * Only required if using ldap driver for identity/assignment
    * python-ldap needs to be installed
* Python 2.7
    * Not tested with newer python versions
 
## Quick Start Guide

Install HQ-Manager into a python environment

```
pip install hq-manager
```

Setup the configuration for the Manager

```yaml
rabbitmq:
  hosts:
    - "10.0.0.1:5672"
    - "10.0.0.2:5672"
    - "10.0.0.3:5672"
  username: "root"
  password: "root"
  virtual_host: "herqles"
sql:
  driver: 'postgres'
  host: '10.0.0.1'
  port: 5432
  database: 'herqles'
  username: 'root'
  password: 'root'
ldap:
  host: "ldap.example.com"
  domain: "example.com"
  base_dn: "DC=example,DC=com"
  bind_username: "bind_user"
  bind_password: "password"
identity:
  mapping:
    "CN=HQ Admins":
      - "herqles.*"
    "CN=HQ Devs":
      - "herqles.task.get"
      - "herqles.job.get"
      - "herqles.worker.get"
  driver:
    module: "hqmanager.identity.ldap_driver"
assignment:
  admin_username: "hq_admin"
  driver:
    module: "hqmanager.assignment.sql_driver"
paths:
  logs: "/var/logs/herqles"
  pid: "/var/run/herqles/manager.pid"
```

Run the Manager

```
hq-manager -c config.yml
```

You now have a fully functional Manager for the Herqles system.
