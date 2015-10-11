#!/usr/bin/env python3

import os,sys,getopt,tarfile
import getpass

from distutils.spawn import find_executable

import time
import socket
import optparse
import subprocess
import multiprocessing

from swiftclient import Connection

from swiftclient import shell
from swiftclient import RequestException
from swiftclient.exceptions import ClientException
from swiftclient.multithreading import OutputManager

try:
    from scandir import walk
except:
    print('importing os.walk instead of scandir.walk')
    from os import walk

swift_auth=os.environ.get("ST_AUTH")
swift_auth_token=os.environ.get("OS_AUTH_TOKEN")
storage_url=os.environ.get("OS_STORAGE_URL")
haz_pigz=False

# define minimum parser object to allow swiftstack shell to run 
def shell_minimal_options():
   global swift_auth,swift_auth_token,storage_url

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
 
   parser.add_option('--os_auth_token',default=swift_auth_token)
   parser.add_option('--os_storage_url',default=storage_url)

   parser.add_option('--os_username')
   parser.add_option('--os_password')
   parser.add_option('--os_auth_url')

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
   parser.add_option('--os_region_name')
   
   parser.add_option('-v', '--verbose', action='count', dest='verbose',
       default=1, help='Print more info.')

   return parser

# wrapper function for swiftstack shell functions
def sw_shell(sw_fun,*args):
   global swift_auth_token,storage_url

   if swift_auth_token and storage_url:
      #args=args+["--os_auth_token",swift_auth_token,
      #   "--os_storage_url",storage_url]
      args=args+("--os_auth_token",swift_auth_token,
         "--os_storage_url",storage_url)

   args = ('',) + args
   with OutputManager() as output:
      parser = shell_minimal_options()
      try:
         sw_fun(parser, list(args), output)
      except (ClientException, RequestException, socket.error) as err:
         output.error(str(err))
 
def sw_download(*args):
   sw_shell(shell.st_download,*args)
 
def sw_upload(*args):
   sw_shell(shell.st_upload,*args)
 
def sw_post(*args):
   sw_shell(shell.st_post,*args)
 
# suffix of archive files
tar_suffix=".tar.gz"
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

# apparently getpid is ok because it's different between mp tasks
def unique_id():
   return str(os.getpid())

def create_tar_file(filename,src_path,file_list):
   global haz_pigz

   # only archive src_path directory
   tar_params=["tar","cvf",filename,"--directory="+src_path,"--no-recursion"]
   if haz_pigz:
      tar_params=tar_params+["--use-compress-program=pigz"]

   # include directory itself in archive for ownership & permissions
   tar_params=tar_params+['.']

   # generate external file list only if files to be archived
   if file_list:
      tmp_file="/tmp/.tar."+unique_id()
      with open(tmp_file,"w") as f:
         for file in file_list:
            f.write("-- \""+file+"\"\n")
      tar_params=tar_params+["-T",tmp_file]
  
   ret=subprocess.call(tar_params)
   if ret>0:
      sys.stderr.write('***** TAR ERROR %s, command: %s *****\n' % 
         (ret,tar_params))   

   if file_list:
      os.unlink(tmp_file)

def upload_file_to_swift(filename,swiftname,container):
   sw_upload("--object-name="+swiftname,
      "--segment-size=2147483648",
      "--use-slo",
      "--segment-container=.segments_"+container,
      "--header=X-Object-Meta-Uploaded-by:"+getpass.getuser(),
      container,filename)

def archive_tar_file(src_path,file_list,container,tmp_dir,pre_path):
   global tar_suffix

   # archive_name is name for archived object
   archive_name=pre_path+tar_suffix
   # temp_archive_name is name of local tar file
   temp_archive_name=unique_id()+os.path.basename(archive_name)
   if tmp_dir:
      temp_archive_name=os.path.join(tmp_dir,temp_archive_name)
  
   # Create local tar file 
   create_tar_file(temp_archive_name,src_path,file_list)

   # Upload tar file to container as 'archive_name' 
   upload_file_to_swift(temp_archive_name,archive_name,container)

   # Delete local tar file
   os.unlink(temp_archive_name)

def is_child_or_sib(dir_name,last_dir):
   dname=os.path.dirname(dir_name) 
   return (dname==last_dir or dname==os.path.dirname(last_dir))

# param order: [src_path,file_list,container,tmp_dir,pre_path]
def archive_worker(item):
   archive_tar_file(item[0],item[1],item[2],item[3],item[4])

def archive_to_swift(local_dir,container,no_hidden,tmp_dir,prefix,par,subtree):
   last_dir=""
   archive=[]

   sw_post(container)

   for dir_name, subdir_list, file_list in mywalk(local_dir):
      rel_path=os.path.relpath(dir_name,local_dir)
      if (not (no_hidden and is_hidden_dir(rel_path))):
         # if files in root directory use basename of root
         if rel_path==".":
            rel_path=os.path.basename(dir_name)+root_id

         if (not subtree) or (is_subtree(subtree,dir_name)):
            archive.append([dir_name,file_list,container,tmp_dir,
               os.path.join(prefix,rel_path)])

         last_dir=dir_name

   archive_pool=multiprocessing.Pool(par)
   archive_pool.map(archive_worker,archive)

# parse name into directory tree
def create_local_path(local_dir,archive_name):
   global tar_suffix

   path=os.path.join(local_dir,archive_name)
   if path.endswith(tar_suffix):
      path=path[:-len(tar_suffix)]

   if not os.path.exists(path):
      os.makedirs(path)
   
   return path

def create_sw_conn():
   global swift_auth,swift_auth_token,storage_url

   if swift_auth_token and storage_url:
      return Connection(preauthtoken=swift_auth_token,preauthurl=storage_url)

   if swift_auth:
      swift_user=os.environ.get("ST_USER")
      swift_key=os.environ.get("ST_KEY")

      if swift_user and swift_key:
         return Connection(authurl=swift_auth,user=swift_user,key=swift_key)

   print("Error: Swift environment not configured!")
   sys.exit()

def extract_tar_file(tarfile,termpath):
   global haz_pigz

   tar_params=["tar","xvf",tarfile,"--directory="+termpath]
   if haz_pigz:
      tar_params=tar_params+["--use-compress-program=pigz"]

   ret=subprocess.call(tar_params)
   if ret > 0:
      sys.stderr.write('***** TAR ERROR %s, command: %s *****\n' % 
         (ret,tar_params))
   
def retrieve_tar_file(tmp_dir,container,obj_name,local_dir,prefix):
   global tar_suffix
   global root_id

   # download tar file and extract into terminal directory
   temp_file=unique_id()+tar_suffix
   if tmp_dir:
      temp_file=os.path.join(tmp_dir,temp_file)

   sw_download("--output="+temp_file,container,obj_name)

   # strip prefix and if next char is /, strip it too
   if prefix and obj_name.startswith(prefix):
      obj_name=obj_name[len(prefix):] 
      if obj_name[0]=='/':
         obj_name=obj_name[1:]
   
   # if bundle, extract using tar embedded paths
   if obj_name.endswith(root_id+tar_suffix):
      term_path=local_dir
   else:
      term_path=create_local_path(local_dir,obj_name)

   extract_tar_file(temp_file,term_path)

   os.unlink(temp_file)

def extract_worker(item):
   retrieve_tar_file(item[0],item[1],item[2],item[3],item[4])

def extract_to_local(local_dir,container,no_hidden,tmp_dir,prefix,par):
   global tar_suffix
   global root_id

   swift_conn=create_sw_conn()
   if swift_conn:
      extract=[]

      try: 
         headers,objs=swift_conn.get_container(container,prefix=prefix,
            full_listing=True)
         for obj in objs:
            if obj['name'].endswith(tar_suffix):
               if no_hidden and is_hidden_dir(obj['name']):
                  continue

               # param order: [tmp_dir,container,obj_name,local_dir,prefix]
               extract.append([tmp_dir,container,obj['name'],local_dir,prefix])
      except ClientException:
         print("Error: cannot access Swift container '%s'!" % container)

      extract_pool=multiprocessing.Pool(par)
      extract_pool.map(extract_worker,extract)

      swift_conn.close()

def usage():
   print("archive [parameters]")
   print("Parameters:")
   print("\t-l local_directory (default .)")
   print("\t-c container (required)")
   print("\t-x (extract from container to local directory)")
   print("\t-n (no hidden directories)")
   print("\t-t temp_dir (directory for temp files)")
   print("\t-a auth_token (default OS_AUTH_TOKEN)")
   print("\t-s storage_url (default OS_STORAGE_URL)")
   print("\t-p prefix")
   print("\t-P parallel_instances (default 3)")

# is path a child of tree?
def is_subtree(tree,path):
   tree_sp=tree.split('/')
   path_sp=path.split('/')

   if len(path_sp)<len(tree_sp):
      return 0

   for t,p in zip(tree_sp,path_sp):
      if t!=p:
         return 0

   return 1

def validate_dir(path,param,tree=""):
   if not os.path.isdir(path):
      print("Error: %s '%s' is not accessible!" % (param,path))
      sys.exit()

   if tree and not is_subtree(tree,path):
      print("Error: '%s' is not in '%s'!" % (path,tree))
      sys.exit()

   if path[-1]=='/':
      path=path[:-1] 

   return(path)

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

def main(argv):
   global swift_auth_token
   global storage_url
   global haz_pigz

   sub_tree=""
   local_dir="."
   container=""
   tmp_dir=""
   extract=False
   no_hidden=False
   prefix=""
   par=3

   try:
      opts,args=getopt.getopt(argv,"l:c:t:a:s:p:P:S:xnh")
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
      elif opt in ("-a"): # override auth_token
         swift_auth_token=arg
      elif opt in ("-s"): # override storage URL
         storage_url=arg
      elif opt in ("-p"): # set prefix
         prefix=arg
      elif opt in ("-P"): # set parallel threads
         par=int(arg)
      elif opt in ("-x"): # extract mode
         extract=True
      elif opt in ("-n"): # set no-hidden flag to skip .*
         no_hidden=True
      elif opt in ("-S"): # specify optional sub-tree
         sub_tree=validate_dir(arg,"subtree",local_dir)
         print("sub_tree param",sub_tree)

   if not container:
      usage()
   else:
      if find_executable("pigz"):
         haz_pigz=True

      if extract:
         extract_to_local(local_dir,container,no_hidden,tmp_dir,prefix,par)
      else:
         archive_to_swift(local_dir,container,no_hidden,tmp_dir,prefix,par,
            sub_tree)

if __name__=="__main__":
   main(sys.argv[1:])
