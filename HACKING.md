# Info about localtuya for developers

This file is to quickly inform developers on localtuya arichtecture so they can quickly and easily target whatever they want to make changes to.


## Installing your customised version of localtuya
You can install your own custom vesion of localtuya including the ability to update to whatever future changes you make via HACS.

First fork the official localtuya github at https://github.com/rospogrigio/localtuya.

Then in your fork change the "name" value in ```hacs.json``` to be a custom name for your fork. This will help differentiate it from the official version of localtuya.

If you haven't already installed HACS into Home Assistant, do so now by following the download link at https://hacs.xyz/

Once HACS is installed login to Home Assistant via the web page and clic on the HACS entry in the menu on the left hand side.

## File layout

```custom_components``` this directory is installed by copying it into the home assistant config directory.

All other files are info about the project or for testing.
The only other file you might want to edit is ```hacs.json``` in order to add a custom name, to differentiate your custom version from the "official" version of localtuya in HACS.

You may also want to edit custom_components/localtuya/manifest.json to use your custom name and to point to your github repo instead of the official one.

