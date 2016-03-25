#! /bin/bash

PATH=swift_commander:$PATH
swc clean
swc env 
swc auth 
swc upload /var/log/samba /swift-commmander-tests/log
swc download /swift-commmander-tests/log ./tests/log
swc archive /var/log/samba /swift-commmander-tests/log.archive
swc unarch /swift-commmander-tests/log.archive ./tests/log.archive
swc search samba /swift-commmander-tests
swc compare ./tests/log ./tests/log.archive
swc rm -rf /swift-commmander-tests/log.archive
swc rm -rf /swift-commmander-tests/log
swc ls /swift-commmander-tests
swc rm -rf /swift-commmander-tests
