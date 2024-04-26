1. clone the repository
```bash
git clone https://github.com/Roguezilla/starboard.git
```
2. **if you are on linux** run this command
```bash
git config core.fileMode false
```
3. **if you are on linux** make sure everything is owned by 1 user if you like running things on different users
4. **if you are on linux** i would recommend chmod 777ing both discpy.py and setup.py so they can create and write files without issues
5. now you have to install the requirements:  
5.1 you can rawdog `requirements.txt` via
`python/python3 -m pip install -r requirements.txt`  
5.2 or you can use pipenv (first create a .venv folder in the starboard folder):  
```bash
pipenv shell # you'll have to run this every time you want to run main.py
pipenv lock
pipenv sync
```
6. after installing the requirements run the setup file (also run `pipenv shell` beforehand if you are using `pipenv` and aren't in its shell somehow):  
```bash
python/python3 setup.py
```
![](https://i.imgur.com/eur3XFq.png)
7. now you must enable the message content intent on your bot's application page:  
![](https://i.imgur.com/qL2etXv.png)
8. give the bot the following permissions:  
**Read Messages/View Channels, Send Messages, Manage Messages, Embed Links, Add Reactions**  
9. final command to setup the bot on your server:   
```bash
sb!setup <archive_channel> <archive_emote> <archive_emote_amount>
```
![](https://i.imgur.com/ex6q23f.png)  