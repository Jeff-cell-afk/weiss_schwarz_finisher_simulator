# Weiss Schwarz Damage Simulator
- This is a finisher simulator project for the Weiss Schwarz TCG
- This is a learning project, goal is to get through iterations to improve it
- Feel free to comment and make any relevant observations

Iteration v1 :
- refresh penalty system
- level zone and level up system
- standard attack trigger system

Iteration v2 :
- this new version now uses classes during the process
- card definition has been reworked, it can now use cards with two soul triggers
- some variables have been renamed to reflect more accurately their usage

Iteration v3
- new model for the system : notebook has been divided between modules to separate more efficiently the whole sequence
- parallelisation has been added to the model to improve efficiency

Iteration v4
- color and events added to the card designation system (not used yet in calculus, but it'll probably come up at some point)
- twin drive mechanic implemented (to be improved later)

All parameters to be manually implemented (usage exemple in main.py)

Objectives and future hopes for later (I don't know if I will get there later, but I will try)
- implementing top deck burns and conditioned damage occurrences in the system
- implementing restand in the system
- implementing icy tail damage in the system
