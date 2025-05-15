# Info about localtuya for developers

This file is to quickly inform developers on localtuya architecture and usage so they can quickly and easily target whatever they want to make changes to.


## Installing your customised version of localtuya
You can install your own custom vesion of localtuya including the ability to update to whatever future changes you make via HACS.

First fork the official localtuya github at https://github.com/rospogrigio/localtuya.

Then in your fork change the "name" value in ```hacs.json``` to be a custom name for your fork. This will help differentiate it from the official version of localtuya.

If you haven't already installed HACS into Home Assistant, do so now by following the download link at https://hacs.xyz/

Once HACS is installed login to Home Assistant via the web page and clic on the HACS entry in the menu on the left hand side.

Now click on the 3 dots in the upper right hand corner of the main page, after the title "Home Assistant Community Store" and select "Custom repositories".

Enter in the https link to your github fork for Repository and select "integration" for Category, then click Add.

It should now be accessable in the list of entries for HACS in the same way that the official one is.


## Updating your customised version of localtuya
Make changes to your localtuya git repo and push them to github.

Next go to the HACS menu entry on the left hand side of the Home Assistant web page.

Find your custom version of localtuya in the list and click on the 3 dots to the right of it, then select "Update Information". You should now see an orange circle with a 1 in it next to the Settings entry in the left hand side menu.

Click on Settings and then at the top there should be an entry to update your custom localtuya. Click on it to bring up a dialog, then click Install, then close the dialog.

Now you should see a "Restart required" entry at the top. Click on this and then Submit to restart Home Assistant. Your updated version of localtuya will start being used when the restart completes.


## File layout

The ```custom_components/localtuya``` directory contains the code for this module. It is basically installed by copying it into the home assistant config directory.

All other files are info about the project or for testing.

You might want to edit ```hacs.json``` in order to add a custom name, to differentiate your custom version from the "official" version of localtuya in HACS.

You may also want to edit custom_components/localtuya/manifest.json to use your custom name and to point to your github repo instead of the official one for help buttons while using your localtuya module.

### Code File layout

// entrypoint for this module?
__init__.py - async_setup, async_migrate_entry, async_setup_entry, async_unload_entry, async_remove_config_entry_device, async_remove_orphan_entities
	prepare_setup_entities, update_listener

// low level code to exchange packets with tuya devices on the local network over TCP
pytuya/__init__.py - TuyaProtocol(asyncio.Protocol, ContextualLogger), EmptyListener(TuyaListener), TuyaListener(ABC)
	MessageDispatcher(ContextualLogger), 
	connect()

// devices and entities
// A device has one or more entities, eg a powerpoint(device) that has 2 switches(2 entities)
// A device is taken as a generic grouping of entities, so only entities need to be
// extended into custom classes for the different kinds of tuya based products.
common.py - TuyaDevice(pytuya.TuyaListener), LocalTuyaEntity(), async_setup_entry
	binary_sensor.py - LocaltuyaBinarySensor(LocalTuyaEntity, BinarySensorEntity)
	climate.py       - LocaltuyaClimate(LocalTuyaEntity, ClimateEntity)
	cover.py         - LocaltuyaCover(LocalTuyaEntity, CoverEntity)
	fan.py           - LocaltuyaFan(LocalTuyaEntity, FanEntity)
	garage_door.py   - LocaltuyaGarageDoor(LocalTuyaEntity, CoverEntity)
	light.py         - LocaltuyaLight(LocalTuyaEntity, LightEntity)
	number.py        - LocaltuyaNumber(LocalTuyaEntity, NumberEntity)
	select.py        - LocaltuyaSelect(LocalTuyaEntity, SelectEntity)
	sensor.py        - LocaltuyaSensor(LocalTuyaEntity)
	switch.py        - LocaltuyaSwitch(LocalTuyaEntity, SwitchEntity)
	vacuum.py        - LocaltuyaVacuum(LocalTuyaEntity, StateVacuumEntity)

// talk to tuya cloud api to get list of tuya devices (including their device ids and local keys)
// it does this via the http verbs: GET, POST, PUT
cloud_api.py - TuyaCloudApi()

// used to initially setup the localtuya integration to be used by home assistant
// used to add all tuya devices/entities (once initial integration has been setup)
config_flow.py - LocaltuyaConfigFlow(config_entries.ConfigFlow), LocalTuyaOptionsFlowHandler(config_entries.OptionsFlow)
	devices_schema, options_schema, schema_defaults, dps_string_list, gen_dps_strings, platform_schema, flow_schema, strip_dps_values, config_schema, validate_input, attempt_cloud_connection

const.py - lost of string values for various constants

// doesnt seem to be called by this module.
// is it called directly via home assistant?
diagnostics.py - async_get_config_entry_diagnostics, async_get_device_diagnostics

// find tuya devices on the local network via UDP broadcast packets.
// i customised this to also find them from a config file since broadcast packets
// may not always make it to the network interface for the docker instance
// that runs home assistant.
discovery.py - TuyaDiscovery(asyncio.DatagramProtocol)
	discover()

// language strings for config_flow webpage GUI
// strings.json should be the same as en.json afaik
strings.json
translations - en.json, it.json, pt-BR.json

// ? used by home assistant somehow ?
manifest.json - used by home assistant for info about the module

// refered by __init__.py
services.yaml - info about "reload" or "set_dp"


## Adding a new tuya product
Although you probably think of a tuya product as a device, home assistant uses the term device to mean a collection of entities.

So to add a new tuya product you need to create a new entity.
Create a file with a lowercase filename like ```<customentity>.py``` in "custom_components/localtuya".

Look at the contents of switch.py or sensor.py for examples of the contents of such files. You will need to add the following to the file:
	1) def flow_schema(dps):
	2) class for your entity, such as "class LocaltuyaCustomEntity(LocalTuyaEntity, SomeBaseEntity):"
	3) async_setup_entry = partial(async_setup_entry, DOMAIN, LocaltuyaSwitch, flow_schema)


const.py list ```PLATFORMS``` contains a list of filenames of entities to add.
(it is only used directly by config_flow.py)
can the entries in this be anything or do they have to be existing types?
it appears they need to be existing components.. but this may be due to how the list is used.
if i try to add "garage_door" it appears to add it successfully, but then the home assistant setup.py file gives an error trying to load it.
if i try to add "button" it appears to be all good, since a "button" component already eists.


!!! while on "Devices" screen for the localtuya integration, there is a "Add Device" button.
clicking on this tries to setup a new integration
Settings -> Devices & Services -> LocalTuya -> X devices -> Add Device.

logs show this:
2023-10-30 23:56:56.145 INFO (MainThread) [custom_components.localtuya.config_flow] LocaltuyaConfigFlow->async_step_user user_input=None



## Changes between official source repo and my code

### root dir of git repo
hacs.json - "Local Tuya" to "Local Tuya - Zak"
info.md - added 'Zak' and some more comments/explanations
README.md - added 'Zak' and some more comments/explanations, fixed weird unicode character in readme
tox.ini - changed "{toxinidir}/localtuya-homeassistant" to "{toxinidir}/localtuya"

### custom_components/localtuya dir of git repo

#### only added comments and debug prints
__init__.py - added debug prints and comments
common.py - changed debug print to warning print

#### important changes
config_flow.py - added "load config from file", added abort config if already configed, plus various comments
cover.py - altered to support my specific garage door opener
discovery.py - added "load config from file"
manifest.json - changed to point to my github repo, changed to my name

