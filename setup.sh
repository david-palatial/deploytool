#!/bin/bash

current_directory=$(pwd)

sudo cp $current_directory/dist/image-builder /usr/local/bin/image-builder
sudo cp $current_directory/dist/sps-client /usr/local/bin/sps-client

mkdir -p ~/.kube
cp $current_directory/dist/cw-kubeconfig ~/.kube/config

if ! grep -q "sps-app='./$current_directory/dist/sps-app'" ~/.bashrc; then
  echo sps-app='./$current_directory/dist/sps-app' >> ~/.bashrc
  source ~/.bashrc

sps-app setup
