#!/bin/bash

# Check if libsecret-1-0 is installed
if ! dpkg-query -W -f='${Status}' libsecret-1-0 | grep "ok installed"; then
  echo "libsecret-1-0 package not found. Exiting..."
  exit 1
fi