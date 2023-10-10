# gowatt
Python class for managing Growatt server sessions.<br/>

Gowatt is a layered client API designed to access and control Growatt SPA/SPH series
Inverters and A/C Couplers.<br/>

It automatically goes through a list of growatt.com servers until login is
successful.  This can be overridden when connecting.<br/>

It uses a layered cache with a half-life of the SPA/SPH's Shine Adapters poll
time.  This ensures that excessive requests to the Growatt Servers are limited.<br/>

All non-time based raw data functions store in the cache on-demand.  All highlevel
functions use the cached data.<br/>

The idea of having a raw API that maps 1:1 to the Growatt Server, and a highlevel API
is to allow for abstraction, and some client stability.  Whether you use the raw or
highlevel functions is based entirely on whether you need stability or variable not
provided at the high level.<br/>

This code is inspired by https://github.com/indykoning/PyPi_GrowattServer<br/>
Tested on an SPA3000.  Dom3442 provided SPH3600 information (Mix).<br/>

# API
```
gowatt(add_random_user_id=False, agent_identifier=None, server_urls=None)
  add_random_user_id = True -> alter the agent_identifier if you have problems
  agent_identifier          -> currently reports it the Brave webbrowser
  server_urls               -> list of additional servers to check (without https://)
All args are OPTIONAL
```

```
login(username,password)
  username = 'firstSecond'
  password = '12345678'
Returns True if logged in.  At this point the PlantId, DeviceSN and DatalogSN are known,
as well as the cache expiry time; this half the datalog interval.
```

The following raw functions are currently implemented, and return various object dicts:<br/>

```
  rawGetDeviceInfo()
  rawGetDevices()
  rawGetEicDevices()
  rawGetPlantData()
  rawGetStatusData()
  rawSet(type, settings)
  rawGetBatChart(date = '2023-10-08')
  rawGetEnergyDayChart(date = '2023-10-08')
  rawGetEnergyMonthChart(date = '2023-10')
  rawGetEnergyYearChart(self,year = '2023')
  rawGetEnergyTotalChart(self,year = '2023')
```

The highlevel API is a work in progress and added as needed.  It is a normalised version of the base data.<br/>

```
  getBatteryChargeRate()
    Returns battery charge rate in Watt Hours as an integer

  getBatteryLevel()
    Returns battery level is a percentage integer

  getDeviceSN()
    Return the device serial number discovered at login

  getDataLogSN()
    Return the data logger serial number discovered at login

  getPlantId()
    Return the plant id discovered at login

  setRuleBatteryFirst(amount,startHour,endHour,enable):
    Sets the amount to charge the battery.
    Only the first schedule is used, all others are zero'd
    
    Parameters:
      amount    -> percentage to charge battery to
      startHour -> when to start
      endHour   -> when to finish
      enable    -> whether rule is enabled or disabled
```

# Example
Very little is needed to get back data.

```
import gowatt

if __name__ == '__main__':  
  session = gowatt.Gowatt();
  
  print('Logging into Growatt')
  success = session.login('username','password')
  if not success:
    print('Failed to log into server')
    quit()
    
  print('Success.')
  
  plantId = session.getPlantId();
  deviceSN = session.getDeviceSN();
  datalogSN = session.getDataLogSN();
  print('Plant ID:',plantId,'\nDevice SN:',deviceSN,'\nDataLog SN:',datalogSN)

  # Example using raw function
  device = session.rawGetStatusData()
  if device:
    print('raw test')
    capacity = int(device['SOC']) - 10
    schedule_settings = ['100',                       # Charging power %
                          str(capacity),              # Stop charging when above SoC %
                          '01', '00',                 # Schedule 1 - Start time
                          '08', '00',                 # Schedule 1 - End time
                          '1',                        # Schedule 1 - Enabled/Disabled (1 = Enabled)
                          '00','00',                  # Schedule 2 - Start time
                          '00','00',                  # Schedule 2 - End time
                          '0',                        # Schedule 2 - Enabled/Disabled (1 = Enabled)
                          '00','00',                  # Schedule 3 - Start time
                          '00','00',                  # Schedule 3 - End time
                          '0']                        # Schedule 3 - Enabled/Disabled (1 = Enabled)
    response = session.rawSet('spa_ac_charge_time_period',schedule_settings)
    print('raw test result:',str(response))

  # Example using highlevel functions
  print('highlevel test')
  capacity = session.getBatteryLevel()
  pCharge = session.getBatteryChargeRate()
  success = session.setRuleBatteryFirst(capacity - 20,1,8,True)
  print('capacity:',capacity,'%   charge rate:',pCharge,'Wh')
  print('highlevel test','passed' if success else 'failed')
```
