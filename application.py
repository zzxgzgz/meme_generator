from flask import Flask, render_template, request, session, flash, redirect, url_for,Markup
import boto3
from PIL import ImageFont
from PIL import Image
from PIL import ImageDraw
from validate_email import validate_email
from boto3.dynamodb.conditions import Key, Attr
import uuid
import os.path
import time
import requests
import re
import json

application = Flask(__name__)
application.secret_key = os.urandom(24)

tableName = 'css_490_final_project_rio'

# create a session with specific keys
# will be used for s3 and dynamodb clients!
# keys will be removed for assignment submission!
aws_session = boto3.Session(
    aws_access_key_id="your_access_key",
    aws_secret_access_key="your_secret_key",
    region_name='us-west-2'
)

# USER SPECIFIC VARS
# the bucket that will store all the memes!

bucketName = "meme-storage-rio"
topicArn = "arn:aws:sns:us-west-2:247395283518:meme-storage-rio"
imageLocationGlobal = "./static/images"
memeSaveLocationGlobal = "./static/images"

imgs = []

# file where the generated meme is saved locally!
# fileLocation = "/tmp/downloadTextFile.txt"

# create a s3 bucket for image host
s3_client = aws_session.client("s3")

# create a sns client to potentially send text messages
sns = aws_session.client('sns')

# dynamodb client
dynamodb = aws_session.resource('dynamodb')


# db table

# table = dynamodb.table


# meme url of the current meme

def setImgs():
    global imgs;
    imgs = [
        url_for('static', filename='images/dimpsey1.jpg'),
        url_for('static', filename='images/dimpsey2.jpg'),
        url_for('static', filename='images/dimpsey3.jpg'),
        url_for('static', filename='images/fahad.jpg'),
        url_for('static', filename='images/doge.jpg'),              
        url_for('static', filename='images/surprise_pickachu.jpg'),
        url_for('static', filename='images/think.jpg'),
        url_for('static', filename='images/trump.jpg'),
        url_for('static', filename='images/goodman.jpg'),
        url_for('static', filename='images/success_kid.jpg'),
        url_for('static', filename='images/unhelpful_teacher.jpg'),
        url_for('static', filename='images/boromir.jpg'),       
        url_for('static', filename='images/good_guy_greg.jpg'),        
        url_for('static', filename='images/wonka.jpg'),
        url_for('static', filename='images/wonka_yao.jpg'),     
        url_for('static', filename='images/college_liberal.jpg'),
        url_for('static', filename='images/10guy.jpg'),
        url_for('static', filename='images/115nfc.jpg'),
        url_for('static', filename='images/alien.jpg'),
        url_for('static', filename='images/black_hmmm.jpg'),
        url_for('static', filename='images/business_cat.jpg'),
        url_for('static', filename='images/chemistry_cat.jpg'),
        url_for('static', filename='images/derpina_eyes_closed.jpg'),
    ]


##update the db URL attribute when a meme is generated.
def updateDB (memeURL, user_name):
    print("in updateDB")
    print("username is: " + user_name)
    # if "user_name" not in session or session["user_name"] == "":
    #     print("why")
    #     return
    table = dynamodb.Table(tableName)
    response = table.query(KeyConditionExpression=Key('email').eq(user_name))
    items = response['Items']
    hasURLs = False

    for i in range (len(items)):
        if 'URLs' in items[i]:
            hasURLs=True
            break
    if (hasURLs):
        result = table.update_item(
    Key={'email':user_name},
    UpdateExpression="SET URLs = list_append(URLs, :i)",
    ExpressionAttributeValues={
        ':i': [memeURL],
    },
        ReturnValues="UPDATED_NEW")
        # print("Updated the list.")
    else:
        # print("No URLs in response.")
        urlList = list()
        urlList.append(memeURL)
        updateResponse = table.update_item(
            Key={'email':user_name},
            UpdateExpression="set URLs = :r",
            ExpressionAttributeValues={
        ':r': [memeURL]
        },
        ReturnValues="UPDATED_NEW"
        )
        # print(updateResponse['ResponseMetadata']['HTTPStatusCode'])



@application.route("/getUrMemes",methods=['GET', 'POST'])
def getUrMemes():
    if (session['user_name']==''):
        return redirect(url_for("login"))
    table = dynamodb.Table(tableName)
    response = table.query(KeyConditionExpression=Key('email').eq(session['user_name']))
    
    for i in response['Items']:
        if 'URLs' in i:
            urls = i['URLs']
            if len(urls)<1:
                flash("You have not created any memes yet!")
            else: 
                for i in range (len(urls)):
                    flash(urls[i])
        else:
            flash('You have not created any memes yet!')
            
    if request.form.get("homePage", False) == "Create more memes!":
        return redirect(url_for('memes'))
    return render_template("getUrMemes.html", username=session['user_name'])


@application.route("/meme_result", methods=['GET', 'POST'])
def meme_result():
    if "user_name" not in session or session["user_name"] == "":
        print("You haven't logged in yet!")
        return redirect(url_for("login"))

    memeURL = session['memeURL']
    updateDB(memeURL, session['user_name'])
    if request.method == "POST":
        if request.form.get("sendText", False) == 'Send Meme via Text':
            phoneNumber = request.form.get('phoneNumber')
            # if not phone number, don't do anything!
            if not phoneNumber:
                return "<h2><font color=\"red\">Phone number can't be empty!</font></h2><br>" + render_template('meme_result.html', imageURL=memeURL)
            else:
                send_image_text(request.form.get('phoneNumber'), memeURL)
                return render_template('meme_result.html', imageURL=memeURL) + "<h2>Check your phone! @" + request.form.get(
                    'phoneNumber') + "</h2>"

        elif request.form.get("homePage", False) == "Create another meme!":
            return redirect(url_for('memes'))

        else:
            return render_template("meme_result.html", imageURL=memeURL)

    else:
        # print("Flashed user name: "+session['user_name'])
        flash(session['user_name'])
        return render_template("meme_result.html", imageURL=memeURL)


# Now the login page is the home page of the Meme Generator
# Route for handling the login page logic
@application.route('/', methods=['GET', 'POST'])
def login():
    setImgs()
    session['images'] = imgs
    error = None
    session['user_name'] = ''
    if request.method == 'POST':
        email_input = request.form['username']
        password_input = request.form['password']
        print('Email: ' + email_input)
        print('PW: ' + password_input)
        if (validate_email(email_input) == False):
            return render_template('login.html', error="Please enter a valid email address to log in.")
        if (len(password_input) < 6):
            return render_template('login.html', error="Password should be at least 6 characters.")
        table = dynamodb.Table(tableName)
        response = table.query(KeyConditionExpression=Key('email').eq(email_input))
        if (len(response['Items']) < 1):
            return render_template('login.html',
                                   error='Account: ' + email_input + ' does not exist, maybe try to register first?')
        accountDetails = response['Items'][0]
        if (accountDetails['email'] == email_input and accountDetails['password'] == password_input):
            print('Logged in!')
            flash(email_input)
            session['user_name'] = email_input
            return redirect(url_for('home'))
        else:
            print('Wrong credentials!')
            return render_template('login.html', error="Invalid username/password for account: " + email_input)
    print("Get in login page, login error:")
    return render_template('login.html', error=error)


@application.route('/register', methods=['GET', 'POST'])
def redirectToRegister():
    return render_template('register.html')


@application.route('/registerNewAccount', methods=['GET', 'POST'])
def registerNewAccount():
    if request.method == 'POST':
        ##user input credentials
        email_input = request.form['email_address']
        password_input = request.form['registrationPassword']
        ##check if input is in valid email format
        if (validate_email(email_input) == False):
            print("Please enter an valid email address.")
            return render_template('register.html', error="Please enter an valid email address.")
        ##does not allow passwords with less than 6 chars
        if (len(password_input) < 6):
            return render_template('register.html', error="Password should be at least 6 characters.")
        ##Retrieve table to see if this account already exist
        table = dynamodb.Table(tableName)
        response = table.query(KeyConditionExpression=Key('email').eq(email_input))
        ## Check if account exist
        if (len(response['Items']) > 0):
            return render_template('register.html',
                                   error="This account: " + email_input + " already exists, please log in.")
        ## insert new record for this new user. 
        response = table.put_item(Item={
            'email': email_input,
            'password': password_input})
        return render_template('register.html',
                               error="Registration for account: " + email_input + " done! Now log in and generate some mEMeS!")
    return render_template('register.html', error=None)


@application.route("/memes", methods=['GET', 'POST'])
def home():
    if "user_name" not in session or session["user_name"] == "":
        print("You haven't logged in yet!")
        return redirect(url_for("login"))

    userName = session['user_name']

    if request.method == "POST":
        # create a meme button
        if request.form.get("createMeme", False) == 'Create Meme':
            if (userName == ''):
                flash("You are redirected to this page because you haven't logged in.")
                return redirect(url_for("login"))
                # return render_template('login.html',error="You haven't logged in yet!")
            print("In the memes page, you have logged in with user name: " + userName)
            topText = request.form.get('topText')
            bottomText = request.form.get('bottomText')
            imageSrc = str(request.form.get('src'))
            print(imageSrc)
            src = imageSrc.replace('/static/images/', '')
            if not topText and not bottomText:  # do nothing if no input in both fields
                return "<h2>Must have text in at least one box!</h2>" + default_home()
            memeURL = create_meme(topText, bottomText, src)
            session['memeURL'] = memeURL
            session["imageURL"] = memeURL
            return redirect(url_for('meme_result'))

            #return render_template('meme_result.html', imageURL=memeURL)
        else:
            return default_home()
    # if nothing is happen, just provide the homepage
    else:
        return default_home()


def default_home():
    session['images'] = imgs
    return render_template("home.html", top_quote="", bottom_quote="", len=len(imgs), imgs=imgs)


# make html image tag
def make_image_tag(imageURL):
    return "<img src =\"" + imageURL + "\">"


def send_image_text(phoneNumber, memeURL):
    # need to have string validation for phoneNumber ie must be 10 characters
    # make a sns subscription from provided phone number
    subscription_response = sns.subscribe(
        TopicArn=topicArn,
        Protocol="sms",
        Endpoint=phoneNumber,
        Attributes={
        },
        ReturnSubscriptionArn=True
    )
    # Publish a simple message to the specified SNS topic
    response = sns.publish(
        TopicArn=topicArn,
        Message=memeURL
    )
    # remove sns subscription so this is effectively a one time text
    sns.unsubscribe(SubscriptionArn=subscription_response['SubscriptionArn'])


# uploads the file obtained through download_file to our s3 bucket
# this s3 bucket needs to be public to access via html and otherwise!
def upload_file_to_bucket(fileLocation, fileName):
    # path to local file, name of bucket to upload to, name file will be in bucket
    s3_client.upload_file(fileLocation, bucketName, fileName, ExtraArgs={'ACL': 'public-read'})


# WARNIING
# things to look out for in this function:
# imageLocation --> where are you getting the image?
# img.save () --> where are you saving the image?
# return value --> what is the bucket you are returning to?
# FONTS! you must have access to font directories (used in memes). this could vary per machine
# builtins.OSError
# for windows go: C:\Windows\Fonts to see which fonts you have...
def create_meme(topText, bottomText, imgName):
    # where the base image is stored! the meme template
    # currently just working with one image
    imageLocation = imageLocationGlobal + "/" + imgName
    img = Image.open(imageLocation)
    # basewidth is the value to scale to (maintaining aspect ratio)
    basewidth = 420
    wpercent = (basewidth / float(img.size[0]))
    hsize = int((float(img.size[1]) * float(wpercent)))
    img = img.resize((basewidth, hsize), Image.ANTIALIAS)
    imageSize = img.size

    # fontName = "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
    # fontName = "DejaVuSans.ttf"
    fontName = "arial.ttf"
    # find biggest font size that works
    fontSize = int(imageSize[1] / 5)
    font = ImageFont.truetype(fontName, fontSize)
    topTextSize = font.getsize(topText)
    bottomTextSize = font.getsize(bottomText)
    while topTextSize[0] > imageSize[0] - 20 or bottomTextSize[0] > imageSize[0] - 20:
        fontSize = fontSize - 1
        font = ImageFont.truetype(fontName, fontSize)
        topTextSize = font.getsize(topText)
        bottomTextSize = font.getsize(bottomText)

    # find top centered position for top text
    topTextPositionX = (imageSize[0] / 2) - (topTextSize[0] / 2)
    topTextPositionY = 0
    topTextPosition = (topTextPositionX, topTextPositionY)

    # find bottom centered position for bottom text
    bottomTextPositionX = (imageSize[0] / 2) - (bottomTextSize[0] / 2)
    bottomTextPositionY = imageSize[1] - bottomTextSize[1]
    bottomTextPosition = (bottomTextPositionX, bottomTextPositionY)

    draw = ImageDraw.Draw(img)

    # draw outlines
    outlineRange = int(fontSize / 15)
    for x in range(-outlineRange, outlineRange + 1):
        for y in range(-outlineRange, outlineRange + 1):
            draw.text((topTextPosition[0] + x, topTextPosition[1] + y), topText, (0, 0, 0), font=font)
            draw.text((bottomTextPosition[0] + x, bottomTextPosition[1] + y), bottomText, (0, 0, 0), font=font)

    draw.text(topTextPosition, topText, (255, 255, 255), font=font)
    draw.text(bottomTextPosition, bottomText, (255, 255, 255), font=font)

    # meme is currently created
    # now assign a UUID to the meme, and upload to the cloud

    memeID = str(uuid.uuid4())

    memeSaveLocation = memeSaveLocationGlobal + '/' + memeID + ".jpg"
    img.save(memeSaveLocation)  # save to some directory

    img.close()

    # wait until this image exists befor uploading to s3
    while not os.path.exists(memeSaveLocation):
        time.sleep(1)

    # need to append ".jpg" to the memeID!
    upload_file_to_bucket(memeSaveLocation, memeID + ".jpg")

    # delete the generated meme locally. it is now stored on the cloud
    if os.path.isfile(memeSaveLocation):
        os.remove(memeSaveLocation)
        
    # jpg extension is important!
    return "https://s3-us-west-2.amazonaws.com/" + bucketName + "/" + memeID + ".jpg"

@application.route("/logout", methods=['GET', 'POST'])
def logout():
    return redirect(url_for("login"))


@application.route("/quote/geek", methods=['GET', 'POST'])
def get_dadjoke():
    session['images'] = imgs
    flash(session['user_name'])
    if request.method == "POST" or request.method == "GET":

        URL = "https://geek-jokes.sameerkumar.website/api"

        getReturn = requests.get(url=URL)
        data = getReturn.json()

        
        # find first word break (space) from the middle
        middle = data.find(" ", int(len(data)/2))
        # split into top and bottom text
        topText, bottomText = data[:middle], data[middle+1:]

        # printing the output
        #print(data)

        return render_template("home.html", top_quote=topText, bottom_quote=bottomText, len=len(imgs), imgs=imgs)
    return render_template("home.html", top_quote="", bottom_quote="", len=len(imgs), imgs=imgs)


@application.route("/quote/dad", methods=['GET', 'POST'])
def get_quote():
    session['images'] = imgs
    flash(session['user_name'])
    if request.method == "POST" or request.method == "GET":
        URL = "https://icanhazdadjoke.com/"

        headers = {'Accept': 'application/json'}
        getReturn = requests.get(url=URL, headers=headers)
        data = getReturn.json()

        joke = data["joke"]
        sentences = re.split(r'[.?]', joke)
        top = ''
        bottom = ''
        print(len(sentences))
        if len(sentences) == 2:
            top = sentences[0]
            bottom = sentences[1]
        else:
            top = sentences[0]
            for x in range(1, len(sentences) - 1):
                bottom += sentences[x] + ". "

        return render_template("home.html", top_quote=top, bottom_quote=bottom, len=len(imgs), imgs=imgs)
    return render_template("home.html", top_quote="", bottom_quote="", len=len(imgs), imgs=imgs)


if __name__ == "__main__":
    application.run(debug=True)
