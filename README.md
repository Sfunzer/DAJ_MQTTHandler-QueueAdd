# Thinking of You Light - Backend Controller


**Introduction**

The “ Thinking of You Light”  is an idea which in its global form is aimed at reducing the feeling of loneliness. The idea is simple: a friend 
or a relative can turn on the light from wherever they are over the world, and the recipient, or "light-keeper" knows someone is 
thinking about him or her because the light is on. 

The application you're looking at is the controller behind the light. this piece of software receives the messages, or as we like to call them 'Little Lights' from a front-end, which 
relays them on to the light-device. It has a few features:

- Queueing 'Little Lights' when multiple are send out at the same time.
- Pausing the relaying of 'Little Lights'. For instance when a receiving user wants to sleep undisturbed.

**Initial Setup**

The initial set-up consist of the following:

*Software*
The software is written in Python, and uses the following library's:

- Paho.MQTT
- Python's Threading
- Python's Time
- Pythons Logging
- Pythons Queue

*Connection*
Both incoming and outgoing messages are send through MQTT. the software can connect with any MQTT broker.

*Future developments*
A few of the futures we are planning to implement on a later moment:

- message acknowledgement by the Light device
- Color control
- Light Animations

**Change-log**

- V1.03 - Service update: code and comment clean-up
- V1.02 - Queueing: 
  - light received are put into the general queue. This queue services both the normal receiving of lights, as the pause function.
- V1.01 - Pausing:
  - Added pause-function: User can now pause the receiving of light.
- V1.00 - Initial Release:
  - Control of Light through front-end.
  - Automatic turn-off after 6.5 seconds.




*Future Developments*
The current code isn't as optimal as it could be. The following is planned in terms of code-maintenance:
- split up into more classes for more modularity
- expand system so it can handle more than one Light-devices

  

**Context**

This development is part of a Fontys FHICT challenge. So any errors or inefficiencies are part of my learning process. 

_If you have any interest in supporting this project, please send a message!_
