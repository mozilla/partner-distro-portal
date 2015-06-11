S3 and Cognito Setup steps:
===========================

- copy config.json.in to config.json
- create a new s3 bucket, add the bucket name to config.json
- create Amazon App on https://sellercentral.amazon.com/
  - add *client* id and secrete to config.json (as app_id and app_secret)
- create cognito identity pool
  - add the identity pool id to config.json
  - under "Authenticated Providers" choose amazon and add the app id
    - use app id from above app (not the client id)
  TODO: future use of personal or FxA?
- create a policy per partner (see below example)
  * attach the role created for the identity pool, likely named Cognito_NAMEAuthRole
  - Each statement must list all identities that have access to this partners objects
  - The first statement for ListBucket must use explicit identities to prevent
    public access, and limits the list to only the first part of the path
  - The second statement provides ListBucket access to specific sub-paths with
    no delimiter.  This returns the full path of all objects under the prefix.
  - The third statement allows GetObject so binaries can be downloaded
  - This pattern allows multiple users per partner by adding more identity values
  TODO: investigate if there is an easy way to pre-fill the identity value
        (without requiring partner to login and retreive it for us)

```  
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Stmt1433458976000",
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::partner-distros"
            ],
            "Condition": {
                "StringEquals": {
                    "cognito-identity.amazonaws.com:sub": [
                        "us-east-1:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                    ],
                    "s3:prefix": [
                        ""
                    ],
                    "s3:delimiter": [
                        "/"
                    ]
                }
            }
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Condition": {
                "StringEquals": {
                    "cognito-identity.amazonaws.com:sub": [
                        "us-east-1:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                    ],
                    "s3:prefix": [
                        "abc/",
                        "def/",
                        "ghi/",
                        "jkl/"
                    ]
                }
            },
            "Resource": [
                "arn:aws:s3:::partner-distros"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject"
            ],
            "Condition": {
                "StringEquals": {
                    "cognito-identity.amazonaws.com:sub": [
                        "us-east-1:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                    ]
                }
            },
            "Resource": [
                "arn:aws:s3:::partner-distros/abc/*",
                "arn:aws:s3:::partner-distros/def/*",
                "arn:aws:s3:::partner-distros/ghi/*",
                "arn:aws:s3:::partner-distros/jkl/*"
            ]
        }
    ]
}
```

Transfering partner binaries from FTP to S3
===========================================

```
bin/scan.py
```

This utility can handle pulling binaries from FTP to a local source, then
transfering them to S3.  It will only grab binaries from the partner build
directories, and only the latest build for a given version.  It has  test mode
where it will scan FTP for partner binaries and simply "touch" those files
locally, this allows faster iteration on testing the rest of the system.

You need to install s3cmd availble from http://s3tools.org/s3cmd (also on
github).  You can install with brew: "brew install s3cmd".  Then add your access
key and secret key (see s3cfg in the partner-dist-portal repo).

Once s3cfg is set, you can run a transfer using:

```
python bin/scan.py -c ./s3cfg
```

By default (ie. hard coded in scan.py), the minimum version that will be
transfered is 38.0.  Also hard coded are the names of current partner
directories that will be transfered.

Running a quick test could look like:

```
python bin/scan.py -c ./s3cfg --scan
python bin/scan.py -c ./s3cfg -j -t
```

The first command will create a json file with all the build paths.  The second
uses that json file, touches the paths locally and syncs those to s3.


Development test server on stackato
===================================

The partner portal can run entirely as a set of static pages, thus can run off
a CDN without any additional server infrastructure.

Access via https://partnerportal.paas.allizom.org/

Using a stackato test server:

Easier to ask me to update.  Otherwise you'll have to probably setup some stuff
on our stackato instance, it uses your mozilla LDAP account, and install a
stackato client.  After that it's easy:

```
stackato login
stackato update partnerportal
```

Preparing static pages for production site:
===========================================

TODO:
  - get a pre-production site setup at https://portal-dev.allizom.org/
  - a script to pull updates from the static branch every so often
  - get a CDN site setup for https://partner-portal.mozilla.org/

- clone the repo into a second directory partner-distro-portal-pages
- git branch static
- run the python server locally (ptyhon app.py)
- run bin/collect
- push to github
- wait for pre-production site to update and test everything
- post a bugzilla bug requesting a pull from pre-production to production
