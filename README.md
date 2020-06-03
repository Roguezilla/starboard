# starboard
starboard can archive anything from messages to images(examples below), it can also embed instagram(because insta embeds love breaking) and reddit(because discord can't embed reddit links properly for some reason).  
run `<>help` to see all the commands
 - first thing you have do is install the requirements and that can be done with:  
```bash
pip install -r requirements.txt
```
 - then you have to create a bot.json file with the following structure:  
```json
{
  "_comment": "create a bot on discord's developer portal to get the token",
  "token": "token",
  "__comment": "you have to apply for a dev account on twitter and create an app to get these keys",
  "twitter": {
    "api_key": "api_key",
    "api_secret": "api_secret",
    "access_token": "access_token",
    "access_token_secret": "access_token_secret"
  }
}
```
 - after you are done with bot.json you can launch the bot and setup it on your server with:
```
<>setup archive_channel archive_emote archive_emote_amount.
```
![setup](https://i.imgur.com/xaPK1wz.png)  

 - bot in action:  
![example](https://i.imgur.com/IcjSd5J.png)
![example2](https://i.imgur.com/nCdA5Ju.png)
