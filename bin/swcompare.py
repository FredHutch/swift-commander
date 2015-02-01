#! /usr/bin/env python3

# Script for comparing the size of a posix folder with the size of a swift folder
#
# swcompare dirkpetersen / Jan 2015 
#

import swiftclient, sys, os, pwd, argparse, subprocess, re, time, datetime, tempfile

try:
    from scandir import walk
except:
    print('importing os.walk instead of scandir.walk')
    from os import walk

class KeyboardInterruptError(Exception): pass

def main():

    currdir = os.getcwd()
    curruser = pwd.getpwuid(os.getuid()).pw_name #os.getenv('USER') does not work in many cron jobs
    tmpdir = tempfile.gettempdir()

    c=create_sw_conn()
    switems=c.get_container(args.container,prefix=args.prefix)
    print(switems)

def create_sw_conn():
    swift_auth=os.environ.get("ST_AUTH")
    swift_user=os.environ.get("ST_USER")
    swift_key=os.environ.get("ST_KEY")
    if swift_auth and swift_user and swift_key:
        return swiftclient.Connection(authurl=swift_auth,user=swift_user,key=swift_key)

def startswithpath(pathlist, pathstr):
    """ checks if at least one of the paths in a list of paths starts with a string """
    for path in pathlist:
        if (os.path.join(pathstr, '')).startswith(path):
            return True
    return False

def getstartpath(pathlist, pathstr):
    """ return the path from pathlist  that is the frist part of pathstr"""
    for path in pathlist:
        if (os.path.join(pathstr, '')).startswith(path):
            return path
    return ''

def getstat(path):
    """ returns the stat information of a file"""
    statinfo=None
    try:
        statinfo=os.stat(path)
    except (IOError, OSError) as e:   # FileNotFoundError only since python 3.3
        if args.debug:
            sys.stderr.write(str(e))
            sys.stderr.write('\nSymbolic link not followed!\n')
    except:
        raise
    return statinfo

def setfiletime(path,attr="atime"):
    """ sets the a time of a file to the current time """
    try:
        statinfo=getstat(path)
        if attr=="atime" or attr=="all":
            os.utime(path,(time.time(),statinfo.st_atime))
        if attr=="mtime" or attr=="all":
            os.utime(path,(time.time(),statinfo.st_mtime))        
        return True
    except Exception as err:
        sys.stderr.write(str(err))
        sys.stderr.write('\n')
        return False

def uid2user(uidNumber):
    """ attempts to convert uidNumber to username """
    import pwd
    try:
        return pwd.getpwuid(int(uidNumber)).pw_name
    except Exception as err:
        sys.stderr.write(str(err))
        sys.stderr.write('\n')
        return str(uidNumber)

def list2file(mylist,path):
    """ dumps a list into a text file, one line per item"""
    try:
        with open(path,'w') as f:
            for item in mylist:
                f.write("{}\r\n".format(item))
        return True
    except Exception as err:
        sys.stderr.write(str(err))
        sys.stderr.write('\n')
        return False

def pathlist2file(mylist,path,root):
    """ dumps a list into a text file, one line per item, but removes
         a root folder from all paths. Used for --files-from feature in rsync"""
    try:
        with open(path,'w') as f:
            for item in mylist:
                f.write("{}\r\n".format(item[len(root):]))
        return True
    except Exception as err:
        sys.stderr.write(str(err))
        sys.stderr.write('\n')
        return False



def send_mail(to, subject, text, attachments=[], cc=[], bcc=['petersen@fhcrc.org',], smtphost="", fromaddr=""):

    if sys.version_info[0] == 2:
        from email.MIMEMultipart import MIMEMultipart
        from email.MIMEBase import MIMEBase
        from email.MIMEText import MIMEText
        from email.Utils import COMMASPACE, formatdate
        from email import Encoders
    else:
        from email.mime.multipart import MIMEMultipart
        from email.mime.base import MIMEBase
        from email.mime.text import MIMEText
        from email.utils import COMMASPACE, formatdate
        from email import encoders as Encoders
    from string import Template
    import socket
    import smtplib

    if not isinstance(to,list):
        print("the 'to' parameter needs to be a list")
        return False    
    if len(to)==0:
        print("no 'to' email addresses")
        return False
    
    myhost=socket.getfqdn()

    if smtphost == '':
        smtphost = get_mx_from_email_or_fqdn(myhost)
    if not smtphost:
        sys.stderr.write('could not determine smtp mail host !\n')
        
    if fromaddr == '':
        fromaddr = os.path.basename(__file__) + '-no-reply@' + \
           '.'.join(myhost.split(".")[-2:]) #extract domain from host
    tc=0
    for t in to:
        if '@' not in t:
            # if no email domain given use domain from local host
            to[tc]=t + '@' + '.'.join(myhost.split(".")[-2:])
        tc+=1

    message = MIMEMultipart()
    message['From'] = fromaddr
    message['To'] = COMMASPACE.join(to)
    message['Date'] = formatdate(localtime=True)
    message['Subject'] = subject
    message['Cc'] = COMMASPACE.join(cc)
    message['Bcc'] = COMMASPACE.join(bcc)

    body = Template('This is a notification message from $application, running on \n' + \
            'host $host. Please review the following message:\n\n' + \
            '$notify_text\n\nIf output is being captured, you may find additional\n' + \
            'information in your logs.\n'
            )
    host_name = socket.gethostname()
    full_body = body.substitute(host=host_name.upper(), notify_text=text, application=os.path.basename(__file__))

    message.attach(MIMEText(full_body))

    for f in attachments:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(open(f, 'rb').read())
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(f))
        message.attach(part)

    addresses = []
    for x in to:
        addresses.append(x)
    for x in cc:
        addresses.append(x)
    for x in bcc:
        addresses.append(x)

    smtp = smtplib.SMTP(smtphost)
    smtp.sendmail(fromaddr, addresses, message.as_string())
    smtp.close()

    return True

def get_mx_from_email_or_fqdn(addr):
    """retrieve the first mail exchanger dns name from an email address."""
    # Match the mail exchanger line in nslookup output.
    MX = re.compile(r'^.*\s+mail exchanger = (?P<priority>\d+) (?P<host>\S+)\s*$')
    # Find mail exchanger of this email address or the current host
    if '@' in addr:
        domain = addr.rsplit('@', 2)[1]
    else:
        domain = '.'.join(addr.rsplit('.')[-2:])
    p = os.popen('/usr/bin/nslookup -q=mx %s' % domain, 'r')
    mxes = list()
    for line in p:
        m = MX.match(line)
        if m is not None:
            mxes.append(m.group('host')[:-1])  #[:-1] just strips the ending dot
    if len(mxes) == 0:
        return ''
    else:
        return mxes[0]

def parse_arguments():
    """
    Gather command-line arguments.
    """

    parser = argparse.ArgumentParser(prog='swcompare',
        description='compare the size of a posix folder with the size ' + \
        'of a swift (pseudo) folder after a data migration ' + \
        '()')
    parser.add_argument( '--posixfolder', '-p', dest='posixfolder',
        action='store',
        help='a folder on a posix file system ',
        default='' )        
    parser.add_argument( '--container', '-c', dest='container',
        action='store',
        help='a container in the swift object store',
        default='' )
    parser.add_argument( '--prefix', '-x', dest='prefix',
        action='store',
        help='a swift object prefix',
        default='' )
    parser.add_argument( '--proc', '-m', dest='maxproc',
        action='store',
        type=int,
        help='maximum number of processes to run ',
        default=0 )
    args = parser.parse_args()
    if not args.posixfolder:
        parser.error('required option --posixfolder not given !')
    if not args.container:
        parser.error('required option --container not given !')
    #if args.debug:
    #    print('DEBUG: Arguments/Options: %s' % args)    
    return args

if __name__ == '__main__':
    # Parse command-line arguments
    args = parse_arguments()
    sys.exit(main())
