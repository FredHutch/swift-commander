swift-commander
===============

swift commander (swc) is a wrapper to various command line client tools 
for openstack swift cloud storage systems. The purpose of swc is 3 fold:

 - provide a very simple user interface to end users 
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

 - `swc` does not implement any authentication but uses a swift authentication environment  setup by `https://github.com/FredHutch/swift-switch-account`
 - if a swift authentication environment is found `swc` creates swift auth_tokens on the fly and uses them with RESTful tools such as curl.

## swc upload 

`swc upload /local_dir/subdir /my_swift_container/subfolder`


wc upload 

