# whatsapp.py

Async bot wrapper for mukulhase WebWhatsapp-Wrapper and adapted from discord.py code format. This module focused on bot usage for WhatsApp.

## Installation

Just download it as zip.

## Basic Usage

```python
import whatsapp

bot = whatsapp.Bot(
    command_prefix="yt!"
)

@bot.command()
async def test(ctx):
    return await ctx.send("Test :V")

if __name__ == "__main__":
    bot.run()
```
It will generate qr.png to scan and start the message websocket.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Please make sure to update tests as appropriate.