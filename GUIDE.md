- clone the repository
```bash
git clone https://github.com/Roguezilla/starboard.git
```
- **if you are on linux** run this command
```bash
git config core.fileMode false
```
- **if you are on linux** make sure everything is owned by 1 user if you like running things on different users
- **if you are on linux** i would recommend chmod 777ing both discpy.py and setup.py so they can create and write files without issues
- now you have to install the requirements:  
```bash
python/python3 -m pip install -r requirements.txt
```
- after installing the requirements run the setup file:  
```bash
python/python3 setup.py
```
![](https://i.imgur.com/eur3XFq.png)
- now that you have this part done you must enable the message content intent on your bot's application page:  
![](https://i.imgur.com/qL2etXv.png)
- when giving permission to the bot you must give at least the following permissions: **Read Messages/View Channels, Send Messages, Manage Messages, Embed Links, Add Reactions**  
- and after that run <>setup and you are good to go 
```bash
sb!setup <archive_channel> <archive_emote> <archive_emote_amount>
```
![](https://i.imgur.com/ex6q23f.png)  