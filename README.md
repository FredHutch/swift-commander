swift-commander
===============

swift commander (swc) is a wrapper to various command line client tools 
for openstack swift cloud storage systems. The purpose of swc is 3 fold:

 - provide a very simple user interface to Linux users
 - provide a unified user interface to swiftclient, curl, etc with reasonale defaults
 - model commands after classic shell tools such as cd, ls, etc.


# Basic Operations

if swc is invoked without any options it shows a basic help page:

```
 Swift Commander (swc) allows you to easily work with a swift object store.
 swc supports sub commands that attempt to mimic standard unix file system tools.
 These sub commands are currently implemented: (Arguments in sqare brackts are 
 optional).

  swc upload <src> <targ>   -  copy file / dirs from a file system to swift
  swc download <src> <targ> -  copy files and dirs from swift to a file system
  swc cd <folder>           -  change current folder to <folder> in swift
  swc ls [folder]           -  list contents of a folder
  swc pwd                   -  display the current swift folder name
  swc rm <path>             -  delete all file paths that start with <path>
  swc cat <file>            -  download a file to TMPDIR and open it with cat
  swc more <file>           -  download a file to TMPDIR and open it with more
  swc less <file>           -  download a file to TMPDIR and open it with less
  swc mkdir <folder>        -  create a folder (works only at the root)
  swc meta <file>           -  display custom meta data of <file>
  swc compare <l.fld> <fld> -  compare size of a local folder with a swift folder  
  swc list <folder> [filt]  -  list folder content (incl. subfolders) and filter
  swc openwith <cmd> <file> -  download a file to TMPDIR and open it with <cmd>
  swc archive <src> <targ>  -  create one tar archive for each folder level
  swc unarch <src> <targ>   -  restore folders that have been archived

 Examples:
  swc upload /local/folder /archive/folder
  swc download /archive/folder /scratch/folder
  swc download /archive/folder $TMPDIR
  swc rm /archive/some_prefix
  swc more /folder/some_file.txt
  swc openwith emacs /folder/some_file.txt
```

## Authentication

 - `swc` does not implement any authentication but uses a swift authentication environment, for example as setup by `https://github.com/FredHutch/swift-switch-account`
 - if a swift authentication environment is found `swc` creates swift auth_tokens on the fly and uses them with RESTful tools such as curl.


## common commands and expected behavior 
 
 - swc rm <folder> works with sub strings not just folder or file names. For example if we have /folder1/folder2/file3.pdf and run `swc rm /folder1/fol` every path that starts with `/folder1/fol` would be deleted. 
 
### swc upload 

use `swc upload /local_dir/subdir /my_swift_container/subfolder` to copy data from a local or networked posix file system to a swift object store. `swc upload` wraps `swift upload` of the standard python swift client:

```
joe@box:~/sc$ swc upload ./testing /test
*** uploading ./test ***
*** to Swift_Account:/test/ ***
executing:swift upload --changed --segment-size=2147483648 --use-slo --segment-container=".segments_test" --header="X-Object-Meta-Uploaded-by:joe" --object-name="" "test" "./test"
*** please wait... ***
/fld11/file12
/fld11/file11
/fld11/fld2/fld3/fld4/file43
/fld11/fld2/fld3/fld4/file42
.

```

the swc wrapper adds the following features:

 - --segment-size ensures that uploads for files > 5GB do not fail. 2147483648 = 2GB
 - Uploaded-by meta data keeps track of the operating system user (often Active Directory user) that upload the data
 - setting --segment-container ensures that containers that carry the segments for multisegment files are hidden if users access these containers with 3rd. party GUI tools (ExpanDrive, Cyberduck, FileZilla) to avoid end user confusion 


as an addional feature you can add multiple meta-data tags to each uploaded object:

```
joe@box:~/sc$ swc upload ./test /test/example/meta project:grant-xyz collaborators:jill,joe,jim cancer:breast
*** uploading ./test ***
*** to Swift_Account:/test/example/meta ***
executing:swift upload --changed --segment-size=2147483648 --use-slo --segment-container=".segments_test" --header="X-Object-Meta-Uploaded-by:petersen" --header=X-Object-Meta-project:grant-xyz --header=X-Object-Meta-collaborators:jill,joe,jim --header=X-Object-Meta-cancer:breast --object-name="example/meta" "test" "./test"
*** please wait... ***
example/meta/fld11/fld2/file21
example/meta/fld11/file11
.
.
/test/example/meta
``` 

These metadata tags stay the swift object store with the data. They are stored just like other important metadata such as change data and name of the object. 

```
joe@box:~/sc$ swc meta example/meta/fld11/file13
       Meta Cancer: breast
Meta Collaborators: jill,joe,jim
  Meta Uploaded-By: petersen
      Meta Project: grant-xyz
        Meta Mtime: 1420047068.977197

```
if setup you can use an external search engine such as ElasticSearch to quickly search for metadata you populated while uploading data

alias: you can use `swc up` instead of `swc upload``


### swc download 

use `swc download /my_swift_container/subfolder /local/subfolder` to copy data from a swift object store to local or network storage. swc download` wraps `swift download` of the standard python swift client:


