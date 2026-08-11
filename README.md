# A Safer Facebook Photo Downloader
This tool is a fork of https://github.com/jcontini/facebook-photos-download/tree/master

I wanted to download all of my tagged photos from Facebook and the [Tagged-Photo-Exporter](https://chromewebstore.google.com/detail/tagged-photo-exporter/cicalpgkgmacgnbnnkhdgpnicipnihgo?hl=en) Google Chrome extension that appears free but then asks for payment while withholding metadata rubbed me the wrong way, so found the original of this tool linked above and made some changes to work on modern (2026) Facebook.

This tool not only works with modern Facebook but doesn't require any of your login info ambiguously entered into Terminal to work and it saves the location data from the Facebook tag too. You do the logging in and the tool does the rest.

1. You run the code.
2. It opens Facebook in Google Chrome
3. You log in and hit Enter
4. The code finds your tagged photos
5. You select the first photo and hit enter
6. The code will index all of your tagged photos and then download them complete with date and location.


##Installation if you know what you're doing with GitHub and Terminal etc:
You'll need to have python, pip3, and [Google Chrome WebDriver](http://chromedriver.chromium.org/downloads) installed to use this tool. Once that's all set up:
1. Clone this repository
2. `cd` into the cloned folder 
3. Run `pip install -r requirements.txt`


##Insallation if you're a novice to all this, haven't done anything like this before and just want your damn photos!:



You will see Chrome open automatically and go to Facebook. From here it's up to you to log in to Facebook with your username and password as normal, solve any captchas and decide what you want to do about cookies etc. The Terminal window will prompt you to press Enter when you're ready and it will navigate to the tagged photos of you page and stop again. This time all you need to do is click on the first photo of you and then return to the Terminal window and press Enter again. That's it!

Your photos will be saved in a "photos" folder where the tool has installed to. This is typically:
YOUR COMPUTER/Users/YOUR USER NAME/facebook-photos-download/photos

[Big ups to the original builders of this this tool and all the people who helped with that :)](https://github.com/jcontini/facebook-photos-download/tree/master)
