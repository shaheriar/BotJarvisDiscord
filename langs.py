from requests import get
import discord
import asyncio

async def pages(ctx, client):
    contents = [" af: afrikaans \n sq: albanian \n am: amharic \n ar: arabic \n hy: armenian \n az: azerbaijani\n eu: basque \n be: belarusian \n bn: bengali \n bs: bosnian \n bg: bulgarian \n ca: catalan \n ceb: cebuano \n ny: chichewa \n zh-cn: chinese (simplified) \n zh-tw: chinese (traditional) \n co: corsican \n hr: croatian \n cs: czech \n da: danish \n nl: dutch\n en: english \n eo: esperanto \n et: estonian \n tl: filipino \n fi: finnish \n fr: french",
                     " fy: frisian \n gl: galician \n ka: georgian \n de: german \n el: greek \n gu: gujarati \n ht: haitian creole \n ha: hausa \n haw: hawaiian \n iw: hebrew \n he: hebrew \n hi: hindi \n hmn: hmong \n hu: hungarian \n is: icelandic \n ig: igbo \n id: indonesian \n ga: irish \n it: italian \n ja: japanese \n jw: javanese \n kn: kannada \n kk: kazakh \n km: khmer \n ko: korean \n ku: kurdish (kurmanji) \n ky: kyrgyz", 
                     " lo: lao \n la: latin \n lv: latvian \n lt: lithuanian \n lb: luxembourgish \n mk: macedonian \n mg: malagasy \n ms: malay \n ml: malayalam \n mt: maltese \n mi: maori \n mr: marathi \n mn: mongolian \n my: myanmar (burmese) \n ne: nepali \n no: norwegian \n or: odia \n ps: pashto \n fa: persian \n pl: polish \n pt: portuguese \n pa: punjabi \n ro: romanian \n ru: russian \n sm: samoan \n gd: scots gaelic \n sr: serbian", 
                     " st: sesotho \n sn: shona \n sd: sindhi \n si: sinhala \n sk: slovak \n sl: slovenian \n so: somali \n es: spanish \n su: sundanese \n sw: swahili \n sv: swedish \n tg: tajik \n ta: tamil \n te: telugu \n th: thai \n tr: turkish \n uk: ukrainian \n ur: urdu \n ug: uyghur \n uz: uzbek \n vi: vietnamese \n cy: welsh \n xh: xhosa \n yi: yiddish \n yo: yoruba \n zu: zulu"]
    pages = 4
    cur_page = 1
    message = await ctx.channel.send(f"__**Page {cur_page}/{pages}**__:\n\n{contents[cur_page-1]}")
    # getting the message object for editing and reacting

    await message.add_reaction("◀️")
    await message.add_reaction("▶️")

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"]
        # This makes sure nobody except the command sender can interact with the "menu"

    while True:
        try:
            reaction, user = await client.wait_for("reaction_add", timeout=60, check=check)
            # waiting for a reaction to be added - times out after x seconds, 60 in this
            # example

            if str(reaction.emoji) == "▶️" and cur_page != pages:
                cur_page += 1
                await message.edit(content=f"__**Page {cur_page}/{pages}**__:\n\n{contents[cur_page-1]}")
                await message.remove_reaction(reaction, user)

            elif str(reaction.emoji) == "◀️" and cur_page > 1:
                cur_page -= 1
                await message.edit(content=f"__**Page {cur_page}/{pages}**__:\n\n{contents[cur_page-1]}")
                await message.remove_reaction(reaction, user)

            else:
                await message.remove_reaction(reaction, user)
                # removes reactions if the user tries to go forward on the last page or
                # backwards on the first page
        except asyncio.TimeoutError:
            await message.delete()
            break
            # ending the loop if user doesn't react after x seconds
