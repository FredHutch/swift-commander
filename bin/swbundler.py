#!/usr/bin/env python3

import os,sys,getopt,tarfile
import getpass

import socket
import optparse
import subprocess

from swiftclient import Connection

from swiftclient import shell
from swiftclient import RequestException
from swiftclient.exceptions import ClientException
from swiftclient.multithreading import OutputManager

swift_auth=os.environ.get("ST_AUTH")

# define minimum parser object to allow swiftstack shell to run 
def shell_minimal_options():
   global swift_auth

   parser = optparse.OptionParser()

   parser.add_option('-A', '--auth', dest='auth',
      default=swift_auth)
   parser.add_option('-V', '--auth-version',
      default=os.environ.get('ST_AUTH_VERSION',
         (os.environ.get('OS_AUTH_VERSION','1.0'))))
   parser.add_option('-U', '--user', dest='user',
      default=os.environ.get('ST_USER'))
   parser.add_option('-K', '--key', dest='key',
      default=os.environ.get('ST_KEY'))
 
   parser.add_option('--os_user_id')
   parser.add_option('--os_user_domain_id')
   parser.add_option('--os_user_domain_name')
   parser.add_option('--os_tenant_id')
   parser.add_option('--os_tenant_name')
   parser.add_option('--os_project_id')
   parser.add_option('--os_project_domain_id')
   parser.add_option('--os_project_name')
   parser.add_option('--os_project_domain_name')
   parser.add_option('--os_service_type')
   parser.add_option('--os_endpoint_type')
   parser.add_option('--os_auth_token')
   parser.add_option('--os_storage_url')
   parser.add_option('--os_region_name')
   
   parser.add_option('-v', '--verbose', action='count', dest='verbose',
       default=1, help='Print more info.')

   return parser

# wrapper function for swiftstack shell functions
def sw_shell(sw_fun,*args):
   args = ('',) + args
   with OutputManager() as output:
      parser = shell_minimal_options()
      try:
         sw_fun(parser, list(args), output)
      except (ClientException, RequestException, socket.error) as err:
         output.error(str(err))
 
def sw_stat(*args):
   sw_shell(shell.st_stat,*args)

def sw_ls(*args):
   sw_shell(shell.st_list,*args)
 
def sw_download(*args):
   sw_shell(shell.st_download,*args)
 
def sw_upload(*args):
   sw_shell(shell.st_upload,*args)
 
def sw_post(*args):
   sw_shell(shell.st_post,*args)
 
# suffix of archive files
tar_suffix=".tar.gz"
bundle_id=".bundle"
root_id=".root"

# True if 1st char of path member is '.' else False
def is_hidden_dir(dir_name):
   for item in dir_name.split('/'):
      if item[0]=='.':
         return True

   return False

def print_flush(str):
   sys.stdout.write(str+'\n')
   sys.stdout.flush()

def create_tar_file(filename,src_path,file_list):
   subprocess.call(["tar","--use-compress-program=pigz","-cvf",filename,
      "--directory="+src_path]+file_list)

def upload_file_to_swift(filename,swiftname,container):
   sw_upload("--object-name="+swiftname,
      "--segment-size=2147483648",
      "--use-slo",
      "--segment-container=.segments_"+container,
      "--header=X-Object-Meta-Uploaded-by:"+getpass.getuser(),
      container,filename)

def append_bundle(tar,src_path,file_list,rel_path):
   for file in file_list:
      src_file=os.path.join(src_path,file)
      tar.add(src_file,os.path.join(rel_path,file))
      print_flush(src_file)

def start_bundle(src_path,file_list,tmp_dir,rel_path,prefix):
   global tar_suffix
   global bundle_id

   # archive_name is name for archived object
   archive_name=os.path.join(prefix,
      os.path.basename(src_path)+bundle_id+tar_suffix)

   #print("creating bundle",archive_name)
   # temp_archive_name is name of local tar file
   temp_archive_name=str(os.getpid())+os.path.basename(archive_name)
   if tmp_dir:
      temp_archive_name=os.path.join(tmp_dir,temp_archive_name)
  
   # Create local tar file 
   tar=tarfile.open(temp_archive_name,"w:gz")
   append_bundle(tar,src_path,file_list,rel_path)

   return temp_archive_name,archive_name,tar

def end_bundle(tar,bundle_name,archive_name,container):
   tar.close()

   # Upload tar file to container as 'archive_name' 
   #print("uploading bundle as",archive_name)
   upload_file_to_swift(bundle_name,archive_name,container)

   os.unlink(bundle_name)

def archive_tar_file(src_path,file_list,container,tmp_dir,pre_path):
   global tar_suffix

   # archive_name is name for archived object
   archive_name=pre_path+tar_suffix
   # temp_archive_name is name of local tar file
   temp_archive_name=str(os.getpid())+os.path.basename(archive_name)
   if tmp_dir:
      temp_archive_name=os.path.join(tmp_dir,temp_archive_name)
  
   # Create local tar file 
   create_tar_file(temp_archive_name,src_path,file_list)

   # Upload tar file to container as 'archive_name' 
   upload_file_to_swift(temp_archive_name,archive_name,container)

   # Delete local tar file
   os.unlink(temp_archive_name)

# return total size of directory's files without children
def flat_dir_size(d,file_list):
   size=0

   for f in file_list:
      ff=os.path.join(d,f)
      if os.path.isfile(ff):
         size=size+os.path.getsize(ff)

   return size

def is_child_or_sib(dir_name,last_dir):
   dname=os.path.dirname(dir_name) 
   return (dname==last_dir or dname==os.path.dirname(last_dir))

def archive_to_swift_bundle(local_dir,container,no_hidden,tmp_dir,bundle,
   prefix):
   bundle_state=0
   last_dir=""

   for dir_name, subdir_list, file_list in os.walk(local_dir):
      rel_path=os.path.relpath(dir_name,local_dir)
      if (not (no_hidden and is_hidden_dir(rel_path)) and file_list):
         dir_size=flat_dir_size(dir_name,file_list)

         if bundle_state and is_child_or_sib(dir_name,last_dir):
            bundle_state=bundle_state+dir_size
            append_bundle(tar,dir_name,file_list,rel_path)

            if bundle_state>=bundle:
               end_bundle(tar,current_bundle,a_name,container)
               bundle_state=0
         else:
            if bundle_state:
               end_bundle(tar,current_bundle,a_name,container)

            if dir_size<bundle:
               current_bundle,a_name,tar=start_bundle(dir_name,file_list,
                  tmp_dir,rel_path,prefix)
               #print("%s: start bundle %s @ %d" % 
               #   (dir_name,current_bundle,dir_size))
               bundle_state=dir_size
            else:
               # if files in root directory use basename of root
               if rel_path==".":
                  rel_path=os.path.basename(dir_name)+root_id

               #print("%s: not in bundle @ %d" % (dir_name,dir_size))
               archive_tar_file(dir_name,file_list,container,tmp_dir,
                  os.path.join(prefix,rel_path))
               bundle_state=0

         last_dir=dir_name

   if bundle_state>0:
      end_bundle(tar,current_bundle,a_name,container)
               
# parse name into directory tree
def create_local_path(local_dir,archive_name):
   global tar_suffix

   path=os.path.join(local_dir,archive_name)
   if path.endswith(tar_suffix):
      path=path[:-len(tar_suffix)]

   if not os.path.exists(path):
      os.makedirs(path)
   
   return path

def extract_to_local(local_dir,container,no_hidden,swift_conn,tmp_dir,prefix):
   global tar_suffix

   try: 
      headers,objs=swift_conn.get_container(container)
      for obj in objs:
         if obj['name'].endswith(tar_suffix):
            if prefix and not obj['name'].startswith(prefix):
               continue

            if no_hidden and is_hidden_dir(obj['name']):
               continue

            # download tar file and extract into terminal directory
            temp_file=str(os.getpid())+tar_suffix
            if tmp_dir:
               temp_file=os.path.join(tmp_dir,temp_file)

            sw_download("--output="+temp_file,container,obj['name'])

            # if bundle, extract using tar embedded paths
            if obj['name'].endswith(bundle_id+tar_suffix) or \
               obj['name'].endswith(root_id+tar_suffix):
               term_path=local_dir
            else:
               term_path=create_local_path(local_dir,obj['name'])

            with tarfile.open(temp_file,"r:gz") as tar:
               tar.extractall(path=term_path)

            os.unlink(temp_file)
   except ClientException:
      print("Error: cannot access Swift container '%s'!" % container)

def create_sw_conn():
   global swift_auth

   swift_user=os.environ.get("ST_USER")
   swift_key=os.environ.get("ST_KEY")

   if swift_auth and swift_user and swift_key:
      return Connection(authurl=swift_auth,user=swift_user,key=swift_key)

   print("Error: Swift environment not configured!")

def usage():
   print("archive [parameters]")
   print("Parameters:")
   print("\t-l local_directory (default .)")
   print("\t-c container (required)")
   print("\t-x (extract from container to local directory)")
   print("\t-n (no hidden directories)")
   print("\t-t temp_dir (directory for temp files)")
   print("\t-b bundle_size (in M or G)")
   print("\t-a auth_token (default ST_AUTH)")
   print("\t-p prefix")

def validate_dir(path,param):
   if not os.path.isdir(path):
      print("Error: %s '%s' is not accessible!" % (param,path))
      sys.exit()

   if path[-1]=='/':
      path=path[:-1] 

   return(path)

def validate_bundle(arg):
   last=arg[-1].upper()
   if last=='M':
      bundle=int(arg[:-1])*1000000
   elif last=='G':
      bundle=int(arg[:-1])*1000000000
   elif last.isdigit():
      bundle=int(arg)
   else:
       print("Error: illegal bundle suffix '%c'" % last)
       sys.exit()

   return bundle

# Fix now unneeded dest param
def main(argv):
   global swift_auth

   local_dir="."
   container=""
   tmp_dir=""
   extract=False
   no_hidden=False
   bundle=0
   prefix=""

   try:
      opts,args=getopt.getopt(argv,"l:c:t:b:a:p:xnh")
   except getopt.GetoptError:
      usage()
      sys.exit()

   for opt,arg in opts:
      if opt in ("-h"):
         usage()
         sys.exit()
      elif opt in ("-l"): # override default local directory
         local_dir=validate_dir(arg,"local")
      elif opt in ("-c"): # set container
         container=arg
      elif opt in ("-t"): # temp file directory
         tmp_dir=validate_dir(arg,"tmp_dir")
      elif opt in ("-b"): # bundle size
         bundle=validate_bundle(arg)
      elif opt in ("-a"): # override auth_token
         swift_auth=arg
      elif opt in ("-p"): # set prefix
         prefix=arg
      elif opt in ("-x"): # extract mode
         extract=True
      elif opt in ("-n"): # set no-hidden flag to skip .*
         no_hidden=True

   if not container:
      usage()
   else:
      if extract:
         swift_conn=create_sw_conn()
         if swift_conn:
            extract_to_local(local_dir,container,no_hidden,swift_conn,tmp_dir,
               prefix)
            swift_conn.close()
      else:
         sw_post(container)
         archive_to_swift_bundle(local_dir,container,no_hidden,tmp_dir,bundle,
            prefix)

if __name__=="__main__":
   main(sys.argv[1:])
