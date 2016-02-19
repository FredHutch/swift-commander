#! /usr/bin/env python3

# Script to save or restore all symlinks in a directory structure to a textfile 
# name: .symbolic-links.tree.txt
#
# swsymlinks dirkpetersen / Aug 2015
#

import sys, os, pwd, argparse, subprocess, re, time, datetime, tempfile
try:
    from scandir import walk
except:
    print('importing os.walk instead of scandir.walk')
    from os import walk

class KeyboardInterruptError(Exception): pass

def main():
    global args

    # Parse command-line arguments
    args = parse_arguments()

    oldcurrdir = os.getcwd()
    os.chdir(args.folder)
    currdir = os.getcwd() 
    curruser = pwd.getpwuid(os.getuid()).pw_name
    tmpdir = tempfile.gettempdir()

    if os.path.abspath(currdir) != os.path.abspath(args.folder):
        print("Current folder %s <> target folder %s, exiting....", (currdir,args.folder))
        return False
    
    fcnt=0
    dcnt=0    
    if args.save:
        print ('\nScanning folder %s to archive symlinks ...' % currdir)
        if args.single:
            # only create one single .symbolic-links.tree.txt at the root
                with open(".symbolic-links.tree.txt",'w') as sfile:
                    dcnt+=1
                    for root, folders, files in mywalk(args.folder):
                        for f in files:
                            try:
                                base=root.replace(currdir+'/','')
                                p=os.path.join(base,f)
                                if os.path.islink(p):
                                    stat=getstat(p)
                                    targ=os.readlink(p)
                                    sfile.write("%s|%s|%s\n" % (p,targ,stat.st_mtime))
                                    fcnt+=1
                                    if args.debug:
                                        sys.stderr.write('SYMLINK:%s\n   TARGET:%s\n' % (p,targ))
                                    
                            except Exception as err:
                                sys.stderr.write(str(err))
                                sys.stderr.write('\n')

        else:
            # create a .symbolic-links.tree.txt in each folder recursively
            for root, folders, files in mywalk(args.folder):
                try:
                    base=root.replace(currdir+'/','')
                    treefile=os.path.join(base,'.symbolic-links.tree.txt')
                    if os.path.exists(treefile):
                        os.remove(treefile)
                    oldroot=''
                except Exception as err:
                    sys.stderr.write(str(err))
                    sys.stderr.write('\n')                    
                for f in files:
                    try:
                        p=os.path.join(base,f)
                        if os.path.islink(p):
                            if oldroot != root:
                                dcnt+=1
                                oldroot=root
                                sys.stderr.write('Symlink Store: %s\n' % (treefile))
                            stat=getstat(p)
                            targ=os.readlink(p)
                            with open(os.path.join(root,'.symbolic-links.tree.txt'),'a') as sfile:
                                sfile.write("%s|%s|%s\n" % (f,targ,stat.st_mtime))
                            fcnt+=1
                            if args.debug:
                                sys.stderr.write('  SYMLINK:%s\n    TARGET:%s\n' % (p,targ))

                    except Exception as err:
                        sys.stderr.write(str(err))
                        sys.stderr.write('\n')
                    
        print("saved %i symlinks into %i .symbolic-links.tree.txt store(s)" % (fcnt, dcnt))

        
    elif args.clean:
        # remove all .symbolic-links.tree.txt files recursively
        cnt=0
        print ('recursively clean .symbolic-links.tree.txt from %s' % currdir)
        for root, folders, files in mywalk(args.folder):            
            if args.debug:
                print ("cleaning folder %s" % root)
            p=os.path.join(root,'.symbolic-links.tree.txt')
            if os.path.exists(p):
                os.remove(p)
                print('deleted %s' % p)                
                cnt+=1
        print('%i .symbolic-links.tree.txt file(s) have been removed.' % cnt)
        
    elif args.restore:
        for root, folders, files in mywalk(args.folder):
            base=root.replace(currdir+'/','')
            treefile=os.path.join(base,'.symbolic-links.tree.txt')
            if os.path.exists(treefile):
                sys.stderr.write('restoring from Symlink Store: %s ...\n ' % (treefile))
                dcnt+=1
                lines=[]
                with open(treefile,'r') as sfile:
                    lines=sfile.readlines()
                for line in lines:
                    try:
                        link,targ,mtime=line.split('|')                    
                        d=os.path.dirname(link)
                        if d:
                            #link was saved with a directory in .symbolic-links.tree.txt
                            if not os.path.exists(d):
                                os.makedirs(d)
                        else:
                            #link was saved as a file only in .symbolic-links.tree.txt
                            link=os.path.join(base,link)
                        if not os.path.islink(link):
                            os.symlink(targ,link)
                            stat=getstat(link)
                            #set both symlink atime and mtime to mtime
                            os.utime(link,(float(mtime),float(mtime)),follow_symlinks=False)
                            fcnt+=1
                            if args.debug:
                                sys.stderr.write('SYMLINK:%s\n   TARGET:%s\n' % (link,targ))
                    except Exception as err:
                        sys.stderr.write(str(err))
                        sys.stderr.write('\n')
        print("Restored %i symlinks from %i .symbolic-links.tree.txt store(s)" % (fcnt, dcnt))
    else:
        print("You need to use either --save, --save --single, --clean or --restore as a command option")

    os.chdir(oldcurrdir)
        

def startswithpath(pathlist, pathstr):
    """ checks if at least one of the paths in a list of paths starts with a string """
    for path in pathlist:
        if (os.path.join(pathstr, '')).startswith(path):
            return True
    return False

def getstartpath(pathlist, pathstr):
    """ return the path from pathlist that is the first part of pathstr"""
    for path in pathlist:
        if (os.path.join(pathstr, '')).startswith(path):
            return path
    return ''

                
def getstat(path):
    """ returns the stat information of a file"""
    statinfo=None
    try:
        statinfo=os.lstat(path)
    except (IOError, OSError) as e:   # FileNotFoundError only since python 3.3
        if args.debug:
            sys.stderr.write(str(e))
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

def mywalk(top, skipdirs=['.snapshot',]):
    """ returns subset of os.walk  """
    for root, dirs, files in walk(top,topdown=True,onerror=walkerr): 
        for skipdir in skipdirs:
            if skipdir in dirs:
                dirs.remove(skipdir)  # don't visit this directory 
        yield root, dirs, files 

def walkerr(oserr):    
    sys.stderr.write(str(oserr))
    sys.stderr.write('\n')
    return 0


def send_mail(to, subject, text, attachments=[], cc=[], bcc=[], smtphost="", fromaddr=""):

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
    parser = argparse.ArgumentParser(prog='swsymlinks',
        description='save or restore all symlinks in a directory structure' +\
               'to a textfile .symbolic-links.tree.txt')
    parser.add_argument( '--save', '-s', dest='save', action='store_true',
        help='save all symlinks to a text file',
        default=False )
    parser.add_argument( '--single', '-n', dest='single', action='store_true',
        help='save all symlinks into a single file .symbolic-links.tree.txt at the root',
        default=False )         
    parser.add_argument( '--clean', '-c', dest='clean', action='store_true',
        help='delete all .symbolic-links.tree.txt files recursively',
        default=False ) 
    parser.add_argument( '--restore', '-r', dest='restore', action='store_true',
        help='restore all symlinks from a text file',
        default=False )
    parser.add_argument( '--debug', '-g', dest='debug', action='store_true',
        help='print the symlink targets to STDERR',
        default=False )        
    parser.add_argument( '--email-notify', '-e', dest='email',
        action='store',
        help='notify this email address of any error ',
        default='' )        
    parser.add_argument( '--folder', '-f', dest='folder',
        action='store', 
        help='search this folder and below for files to remove')
    args = parser.parse_args()
    if not args.folder:
        parser.error('required option --folder not given !')
    if args.debug:
        print('DEBUG: Arguments/Options: %s' % args)    
    return args

if __name__ == '__main__':
    sys.exit(main())
