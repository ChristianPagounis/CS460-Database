######################################
# author ben lawson <balawson@bu.edu>
# Edited by: Craig Einstein <einstein@bu.edu>
######################################
# Some code adapted from
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################

import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
import flask_login

import html
import logging
from operator import itemgetter
from passlib.hash import sha256_crypt

#for image uploading
import os, base64

logger = logging.getLogger('photoshare')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(name)s:%(levelname)s:%(funcName)s:%(lineno)d: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

mysql = MySQL()
app = Flask(__name__, static_url_path="/static")
app.secret_key = 'super secret string'  # Change this!

#These will need to be changed according to your creditionals
#
# NOTE: DON'T commit the next four lines of code.  Use 'git add -p' to go around
#       this section
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'cs460'
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

#begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from Users")
users = cursor.fetchall()

def getUserList():
    cursor.execute("SELECT email from Users")
    return cursor.fetchall()

class User(flask_login.UserMixin):
    def __init__(self):
        is_authenticated = False

    def is_authenticated(self):
        return self.is_authenticated

    def set_auth_status(self, status: bool):
        self.is_authenticated = status

@login_manager.user_loader
def user_loader(email):
    users = getUserList()
    if not(email) or email not in str(users):
        return
    user = User()
    user.id = email
    return user

@login_manager.request_loader
def request_loader(request):
    users = getUserList()
    email = request.form.get('email')
    if not(email) or email not in str(users):
        return
    user = User()
    user.id = email
    cursor = mysql.connect().cursor()
    cursor.execute("SELECT password_hash FROM Users WHERE email = '{0}'".format(email))
    data = cursor.fetchall()
    pwd_hash = str(data[0][0] )
    user.set_auth_status(sha256_crypt.verify(request.form['password'], pwd_hash))
    return user

'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
    return new_page_html
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'GET':
        return '''
               <form action='login' method='POST'>
                <input type='text' name='email' id='email' placeholder='email'></input>
                <input type='password' name='password' id='password' placeholder='password'></input>
                <input type='submit' name='submit'></input>
               </form></br>
           <a href='/'>Home</a>
               '''
    #The request method is POST (page is recieving data)
    email = flask.request.form['email']
    #check if email is registered
    if cursor.execute(f"SELECT password_hash FROM Users WHERE email = '{email}'"):
        data = cursor.fetchall()
        pwd_hash = str(data[0][0])
        if sha256_crypt.verify(request.form['password'], pwd_hash):
            user = User()
            user.id = email
            flask_login.login_user(user) #okay login in user
            return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

    #information did not match
    return "<a href='/login'>Try again</a>\
            </br><a href='/register'>or make an account</a>"

@app.route('/logout')
def logout():
    flask_login.logout_user()
    return render_template('hello.html', message='Logged out')

@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('unauth.html')

#you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
    return render_template('register.html', supress='True')

@app.route("/register", methods=['POST'])
def register_user():
    try:
        email=request.form.get('email')
        password=request.form.get('password')
        first_name=request.form.get('fname')
        last_name=request.form.get('lname')
        gender=request.form.get('gender').lower()
        birthdate=request.form.get('dob')
        hometown=request.form.get('hometown')
    except:
        logger.error("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
        return flask.redirect(flask.url_for('register'))
    test =  isEmailUnique(email)
    if test:
        cursor.execute(
        "INSERT INTO Users "
        "(email, password_hash, first_name, last_name, gender, dob, hometown, contrib_score)"
        " VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}', 0)"
                .format(email, sha256_crypt.hash(password),
                        first_name, last_name, gender, birthdate, hometown))
        conn.commit()
        #log user in
        user = User()
        user.id = email
        flask_login.login_user(user)
        return render_template('hello.html', name=first_name, message='Account Created!')
    else:
        return flask.render_template('register.html', supress=False)

def getUsersPhotos(uid):
    cursor.execute("""
    SELECT img_data, picture_id, caption
    FROM Pictures
    WHERE owner_id = '{0}'
    """.format(uid))
    return cursor.fetchall() #NOTE list of tuples, [(imgdata, pid), ...]

def getUserIdFromEmail(email):
    cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
    return cursor.fetchone()[0]

def isEmailUnique(email):
    #use this to check if a email has already been registered
    if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
        #this means there are greater than zero entries with that email
        return False
    else:
        return True
#end login code

@app.route('/profile')
@flask_login.login_required
def protected():
    uid = flask_login.current_user.id
    query = "SELECT first_name FROM Users WHERE email = '{0}'".format(uid)
    cursor.execute(query)
    name = cursor.fetchone()[0]
    return render_template('hello.html', name=name,
                           message="Here's your profile")

################################################################################
#                            Useful helper methods                             #
################################################################################
def getUsersAlbumsFromId(email):
    """
    Get the user's albums for photo uploading.

    Parameters:
    email: the email of the user whose albums are desired

    Return value:
    The names of all this user's albums
    """

    numeric_uid = getUserIdFromEmail(email)

    query = """
    SELECT album_name
    FROM Albums
    WHERE owner_id = {0}
    """.format(numeric_uid)
    results = cursor.execute(query)
    rows = cursor.fetchall()

    return rows


def getAlbumId(name, uid):
    """
    Return an album's unique numeric ID.

    Parameters:
    name: the human-readable name of the album
    uid: the numeric ID of the album owner (because two users can have albums
         with the same name)

    Return:
    The numeric ID of this album, or None if no such album is associated with
    the given UID
    """
    query = """
    SELECT album_id
    FROM Albums
    WHERE owner_id = {0} AND album_name = '{1}'
    """.format(uid, name)
    cursor.execute(query)
    return cursor.fetchone()[0]

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS
################################################################################
#                              End helper methods                              #
################################################################################


################################################################################


################################################################################
#                                 Tag methods                                  #
################################################################################
@app.route('/tags/')
def view_all_tags():
    query = """
    SELECT COUNT(W.picture_id), T.tag_text, T.tag_id
    FROM Tagged_with W
    JOIN Tags T ON W.tag_id = T.tag_id
    GROUP BY W.tag_id
    ORDER BY COUNT(picture_id) DESC
    """
    cursor.execute(query)
    tags = cursor.fetchall()

    return render_template('tags.html', tags=tags)


@app.route('/tags/top-five')
def list_top_five_tags():
    query = """
    SELECT COUNT(W.picture_id), T.tag_text, T.tag_id
    FROM Tagged_with W
    JOIN Tags T ON W.tag_id = T.tag_id
    GROUP BY W.tag_id
    ORDER BY COUNT(picture_id) DESC
    LIMIT 5
    """
    cursor.execute(query)
    tags = cursor.fetchall()

    return render_template('popular_tags.html', tags=tags)


def get_photos_by_tag(tag_id, current_user):
    """
    Get all the photos for a tag.

    Parameters:
    tag_id: numeric ID of the desired tag
    current_user: whether to get photos with the desired tag that belong to only
    the current_user (True) or everyone (False)

    Return: a list of all the pictures associated with a single tag, with the
    the scope as determined by the value of current_user
    """
    pictures = []

    if current_user:
        uid = getUserIdFromEmail(flask_login.current_user.id)
        query = """
        SELECT concat(U.first_name, ' ', U.last_name), P.picture_id, P.img_data,
               P.album_id, P.owner_id, A.album_name
        FROM Albums A
        JOIN Users U ON U.user_id = A.owner_id
        JOIN Pictures P ON A.album_id = P.album_id
        JOIN Tagged_with T ON P.picture_id = T.picture_id
        WHERE T.tag_id = {0} AND P.owner_id = {1}
        """.format(tag_id, uid)
        cursor.execute(query)
        pictures = cursor.fetchall()
    else:
        query = """
        SELECT concat(U.first_name, ' ', U.last_name), P.picture_id, P.img_data,
               P.album_id, P.owner_id, A.album_name
        FROM Albums A
        JOIN Users U ON U.user_id = A.owner_id
        JOIN Pictures P ON A.album_id = P.album_id
        JOIN Tagged_with T ON P.picture_id = T.picture_id
        WHERE T.tag_id = {0}
        """.format(tag_id)
        cursor.execute(query)
        pictures = cursor.fetchall()

    # we want to grab the tag text no matter the scope of the pictures retrieved
    query = """
    SELECT tag_text
    FROM Tags
    WHERE tag_id = {0}
    """.format(tag_id)
    cursor.execute(query)
    tag_text = cursor.fetchone()[0]

    return pictures, tag_text


@app.route('/tags/view/<int:tag_id>', methods=['GET', 'POST'])
def view_tag(tag_id):
    """
    Show all the pictures for a given tag.

    Parameters:
    tag_id: the numeric ID of the desired tag
    """
    if request.method == "GET":
        # by default, get all pictures with this tag
        pictures, tag_text = get_photos_by_tag(tag_id, False)
    else:
        all_users = request.form.get('all-user-toggle')
        # In the HTML template, there is a checkbox called all-user-toggle, and
        # we can check it to figure out what scope of pictures to show.  This is
        # straightforward enough, but for some reason, there seems to be no
        # "off" value --- if the box is unchecked, the value is None... weird
        # but whatever
        if all_users == "on":   # checkbox is checked, so get all pictures
            pictures, tag_text = get_photos_by_tag(tag_id, False)
        elif all_users is None: # checkbox unchecked, get only user's pictures
            pictures, tag_text = get_photos_by_tag(tag_id, True)

    return render_template("view_tag.html", pictures=pictures, tag=tag_text,
                           base64=base64)

def tag_exists(tag):
    """
    Check whether a tag exists.

    Parameters:
    tag: the *text* of the tag to check for: the user has no way of knowing the
    tag ID---they only know and care about the text

    Return: True if a tag with the queried text exists; False otherwise
    """
    query = """
    SELECT *
    FROM Tags WHERE tag_text = '{0}'
    """.format(tag.lower())
    results = cursor.execute(query)
    # When executing a SELECT query, cursor.execute(...) by itself (before a
    # fetch*) returns the number of rows matching the query.  This means that if
    # it returns 0, there is no row that contains a tag_text attribute matching
    # the search query.  This return statement is therefore equivalent to
    # if results > 0:
    #     return True
    # else:
    #     return False
    return (results > 0)


@app.route('/tags/search', methods=['get', 'post'])
def search_photo_by_tag():
    """
    Find photos with the associated tag(s).

    Return:
    photos associated with the given tag(s)
    """
    if request.method == 'GET':
        return render_template('tag_search.html')
    else:
        # get the comma-separated list of tags as a string
        tags = request.form.get('tags')

        # returns the tags string as a list, split on ", "
        tags = tags.split(", ")
        # we can define helper methods inside functions to keep the external
        # interface cleaner
        def get_tag_id(tag_text):
            """
            Get the numeric ID of a tag given its text form.

            Parameters:
            tag_text: the string of the tag to get the ID for

            Return: the associated tag_id if a tag with the given text exists;
            None otherwise
            """
            query = """
            SELECT tag_id
            FROM Tags T
            WHERE T.tag_text = '{0}'
            """.format(tag_text)
            cursor.execute(query)
            record = cursor.fetchone()
            # fetchone() can return None, if executing a SELECT query yields no
            # rows; we can only index the record if it's not None
            if record is not None:
                return record[0]

        # Might contain values that are None, as detailed above
        all_tag_ids = [get_tag_id(t) for t in tags]
        # filter out None values (nonexistent tags)
        tag_ids = filter(lambda x: x is not None, all_tag_ids)
        # clean up the list with only non-None values, because tag_ids is not
        # actually an iterable like a list is --- we CANNOT index it
        valid_tag_ids = [x for x in tag_ids]

        # equivalent to
        # if len(all_tag_ids) == len(valid_tag_ids):
        #     count_tag_ids = len(valid_tag_ids)
        # else:
        #     count_tag_ids = 0
        # but more concise
        count_tag_ids = len(valid_tag_ids) if len(all_tag_ids) ==\
        len(valid_tag_ids) else 0

        # user's query failed, because what is valid is different
        # from what the user *actually* asked for, regardless if there are
        # any valid tags --- spec sheet says we must match ALL tags queried
        if count_tag_ids == 0:
            message = "There are no photos with all of the following tags: "
            for t in tags:
                message += f"\"{t}\" "
            return render_template('hello.html', message=message)

        # we're going to use this over and over, so we save it in a variable
        # for easy reference and to not repeat ourselves
        base_query = """
        SELECT DISTINCT picture_id
        FROM Tagged_with
        WHERE tag_id = {0}
        """

        # we start with one tag
        pid_query = base_query.format(valid_tag_ids[0])
        for i in range(1, count_tag_ids - 1):
            # don't go all the way to count_tag_ids, because it will lead to
            # a malformed statement and subsequently syntax error
            #
            # if count_tag_ids is 1, we have range(1, 0), so this won't fire,
            # thus implementing single-tag search
            #
            # this statement does repeated filtering to find pictures that have
            # all the tags the user requested
            pid_query += " AND picture_id IN " + "(" + \
                base_query.format(valid_tag_ids[i]) + ")"
        # if we have more than one tag, we need to make sure we search on the
        # last tag
        if count_tag_ids > 1:
            pid_query += " AND picture_id IN " + "(" + \
            base_query.format(valid_tag_ids[-1]) + ")"

        # picture, uploader, and album data for the matching pictures
        query = """
        SELECT DISTINCT concat(U.first_name, ' ', U.last_name),
        P.picture_id, P.img_data,
        P.album_id, P.owner_id, A.album_name
        FROM Albums A
        JOIN Users U ON U.user_id = A.owner_id
        JOIN Pictures P ON A.album_id = P.album_id
        JOIN Tagged_with T ON P.picture_id = T.picture_id
        WHERE P.picture_id IN ({0})
        """.format(pid_query)

        cursor.execute(query)

        pictures = cursor.fetchall()

        return render_template('view_multi_tagged.html', base64=base64,
                               tags=tags, pictures=pictures)


################################################################################
#                               End tag methods                                #
################################################################################


################################################################################


################################################################################
#                          Individual photo methods                            #
################################################################################
# photos uploaded using base64 encoding so they can be directly embeded in HTML
@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
    if request.method == 'POST':
        uid = getUserIdFromEmail(flask_login.current_user.id)
        imgfile = request.files['photo']
        caption = request.form.get('caption')
        tags = request.form.get('tags').split(', ')
        album_name = request.form.get('album_name')
        album_id = getAlbumId(album_name, uid)
        photo_data = None
        if imgfile and allowed_file(imgfile.filename):
            photo_data =imgfile.read()
        else:
            file_ext = imgfile.filename.rsplit(".", 1)[1]
            message = f"""forbidden format '.{file_ext}'"""
            return render_template('hello.html',
                                   message=message)
        query = """
        INSERT INTO Pictures (album_id, owner_id, img_data, caption)
        VALUES (%s, %s, %s, %s)
        """
        data = (album_id, uid, photo_data, caption)
        cursor.execute(query, data)
        conn.commit()

        # admittedly a hacky way to pick off the picture ID for tagging purposes
        query = """
        SELECT MAX(picture_id)
        FROM Pictures
        WHERE owner_id = %s AND album_id = %s
        """
        data = (uid, album_id)
        result = cursor.execute(query, data)
        picture_id = cursor.fetchone()[0]

        for t in tags:
            tag_id = None
            if not tag_exists(t): # adding a new tag
                query = """
                INSERT INTO Tags (tag_text) VALUES ('{0}')
                """.format(t.lower())
                cursor.execute(query)
                conn.commit()

                query = """     # getting new tag ID; again, hacky
                SELECT MAX(tag_id)
                FROM Tags
                """
                result = cursor.execute(query)
                tag_id = cursor.fetchone()[0]
            else:               # tagging a pic with an existing tag
                query = """
                SELECT tag_id
                FROM Tags
                WHERE tag_text = '{0}'
                """.format(t.lower())
                result = cursor.execute(query)
                tag_id = cursor.fetchone()[0]

            # actually tagging the photo
            query = """
            INSERT INTO Tagged_with (picture_id, tag_id)
            VALUES ({0}, {1})
            """.format(picture_id, tag_id)
            result = cursor.execute(query)
            conn.commit()

        return render_template('hello.html',
                               name=flask_login.current_user.id,
                               message='Photo uploaded!',
                               photos=getUsersPhotos(uid),base64=base64)
    #The method is GET so we return a  HTML form to upload the a photo.
    else:
        rows = getUsersAlbumsFromId(flask_login.current_user.id)
        return render_template('upload.html', rows=rows)


@app.route('/photos/view/<int:photo_id>', methods=['GET', 'POST'])
def view_photo(photo_id):
    """
    View a photo.

    Parameters:
    photo_id: the ID of the photo to view
    """

    # grab the picture, caption and uploader name first
    query = """
    SELECT P.img_data, P.caption, concat(U.first_name, ' ', U.last_name),
           P.owner_id
    FROM Pictures P JOIN Users U on P.owner_id = U.user_id
    WHERE P.picture_id = {0}
    """.format(photo_id)

    results = cursor.execute(query)
    # picture ID is unique, so fetch only one (there should only be one to start
    # with)
    photo = cursor.fetchone()

    # then grab social...
    # tags first
    query = """
    SELECT T.tag_id, T.tag_text
    FROM Tags T
    JOIN Tagged_with W ON T.tag_id = W.tag_id
    WHERE W.picture_id = {0}
    """.format(photo_id)
    cursor.execute(query)
    tags = cursor.fetchall()

    # then like count and names of people who liked the photo
    query = """
    SELECT L.user_id, concat(U.first_name, ' ', U.last_name) as name
    FROM Likes L JOIN Users U ON L.user_id = U.user_id
    WHERE picture_id = {0}
    """.format(photo_id)
    results = cursor.execute(query)
    likes = cursor.fetchall()
    likes_ids = [tup[0] for tup in likes] # a nice, clean list of ints
    likes_names = [tup[1] for tup in likes] # ditto, but now strings

    # and finally comments
    # descending on id, because the largest id is the newest --- we display the
    # comments from newest to oldest
    query = """
    SELECT C.post_date, C.text, concat(U.first_name, ' ', U.last_name)
    FROM Comments C JOIN Users U ON C.author_id = U.user_id
    WHERE C.picture_id = {0}
    ORDER BY C.comment_id DESC
    """.format(photo_id)
    results = cursor.execute(query)
    comments = cursor.fetchall()

    if request.method == "GET":
        return render_template("view_photo.html", photo=photo, base64=base64,
                               comments=comments, likes_names=likes_names,
                               tags=tags, like_count=len(likes), html=html)
    else:                       # POST (either comment or like)
        uid = getUserIdFromEmail(flask_login.current_user.id)
        if request.form.getlist('like') != []: # like button
            if uid in likes_ids:    # user has already liked this photo
                message = "You've already liked this photo!"
                return render_template('view_photo.html', photo=photo,
                                       base64=base64, comments=comments,
                                       likes=likes, like_count=len(likes),
                                       likes_names=likes_names, message=message,
                                       tags=tags, html=html)
            else:               # user has not liked this photo yet
                if uid == photo[3]: # user is the uploader, not allowed to like
                    message = "You can't like your own photo!"
                    return render_template('view_photo.html', photo=photo,
                                           base64=base64, comments=comments,
                                           likes=likes, like_count=len(likes),
                                           likes_names=likes_names,
                                           message=message, html=html)
                else:           # user not uploader, valid like
                    # record the like
                    query = """
                    INSERT INTO Likes (user_id, picture_id) VALUES
                    ({0}, {1})
                    """.format(uid, photo_id)
                    cursor.execute(query)
                    conn.commit()

                    # update like count, refresh page
                    query = """
                    SELECT L.user_id,
                           concat(U.first_name, ' ', U.last_name) as name
                    FROM Likes L JOIN Users U ON L.user_id = U.user_id
                    WHERE picture_id = {0}
                    """.format(photo_id)
                    results = cursor.execute(query)
                    likes = cursor.fetchall()
                    likes_ids = [tup[0] for tup in likes]
                    likes_names = [tup[1] for tup in likes]

                    return render_template('view_photo.html', photo=photo,
                                           base64=base64, comments=comments,
                                           likes=likes, like_count=len(likes),
                                           likes_names=likes_names, html=html)
        else:                   # comment button
            if uid == photo[3]: # user is uploader; prevent them from commenting
                message = "You may not comment on your own photo"
                return render_template('view_photo.html', photo=photo,
                                       base64=base64, comments=comments,
                                       likes=likes, like_count=len(likes),
                                       likes_names=likes_names, message=message)
            else:               # user is not uploader; allow them to comment
                comment_text = request.form.get('comment')
                query = """
                INSERT INTO Comments (author_id, picture_id, post_date, text)
                VALUES ({0}, {1}, CURDATE(), '{2}')
                """.format(uid, photo_id,
                           html.escape(comment_text, True))
                cursor.execute(query)
                conn.commit()
                query = """
                SELECT C.post_date, C.text,
                       concat(U.first_name, ' ', U.last_name)
                FROM Comments C JOIN Users U ON C.author_id = U.user_id
                WHERE C.picture_id = {0}
                ORDER BY C.comment_id DESC
                """.format(photo_id)
                results = cursor.execute(query)
                comments = cursor.fetchall()
                message = "Comment posted!"
                return render_template('view_photo.html', photo=photo,
                                       base64=base64, comments=comments,
                                       likes=likes, like_count=len(likes),
                                       likes_names=likes_names,
                                       message=message, html=html)


@flask_login.login_required
@app.route('/photos/delete/')
def delete_photo_show_form():
    """
    Show a form to allow a user to select a photo to delete
    """
    uid = getUserIdFromEmail(flask_login.current_user.id)
    query = """
    SELECT picture_id, album_id, img_data, caption
    FROM Pictures
    WHERE owner_id = {0}
    ORDER BY album_id
    """.format(uid)

    cursor.execute(query)
    pics = cursor.fetchall()

    return render_template('delete-photo.html',
                           base64=base64, pics=pics)


@flask_login.login_required
@app.route('/photos/delete/<int:pic_id>', methods=['POST'])
def delete_photo(pic_id, batch=False):
    """
    Delete a photo.

    Parameters:
    pic_id: the ID of the picture to delete
    batch: whether this is part of a mass delete (as in the deletion of an
    album).  When False, shows to the user a new page with a confirmation
    message.  When True, does not show confirmation page, as that would be
    clunky and jarring.  Default: False
    """
    # delete likes first, because Likes has a foreign key on Pictures, so trying
    # to delete Pictures immediately will result in an error
    query = """
    DELETE FROM Likes
    WHERE picture_id = {0}
    """.format(pic_id)
    cursor.execute(query)
    conn.commit()

    # delete tag relations next, for the same reason
    query = """
    DELETE FROM Tagged_with
    WHERE picture_id = {0}
    """.format(pic_id)
    cursor.execute(query)
    conn.commit()

    # now we can delete the photo itself
    query = """
    DELETE FROM Pictures
    WHERE picture_id = {0}
    """.format(pic_id)

    cursor.execute(query)
    conn.commit()

    if not batch:
        message = "Photo deleted!"
        return render_template('hello.html', message=message)

################################################################################
#                         End individual photo methods                         #
################################################################################


################################################################################


################################################################################
#                                Album methods                                 #
################################################################################
@app.route('/albums/create', methods=['GET', 'POST'])
@flask_login.login_required
def create_album():
    """ Create a new album. """
    if request.method == 'POST':
        # user typed something into the box and hit "Submit"/pressed Enter
        new_album_name = request.form.get('album-name')

        uid = getUserIdFromEmail(flask_login.current_user.id)

        # check the user doesn't have an album with this name already (mostly
        # for user convenience, as names need not be unique)
        query = """
        SELECT album_name
        FROM Albums
        WHERE owner_id = {0};
        """.format(uid)
        data = cursor.execute(query)
        album_names = cursor.fetchall()
        for tuple in album_names:
            name = tuple[0]
            if name == new_album_name:
                # prints a message to the user that they already have an album
                # with the entered name
                return render_template('create_album.html', exists=True)

        # if we get here, user does not have an album with this name
        query = """
        INSERT INTO Albums (album_name, owner_id, creation_date) VALUES
        ('{0}', {1}, CURDATE())
        """.format(new_album_name, uid)
        results = cursor.execute(query)
        conn.commit()

        return render_template('hello.html')
    else:
        return render_template('create_album.html')


""" View all albums (public; guests can view these too) """
@app.route('/albums/', methods=['GET'])
def view_all_albums():
    query = """
    SELECT A.album_id, A.album_name, A.owner_id,
    concat(U.first_name, ' ', U.last_name) as name
    FROM Albums A JOIN Users U ON A.owner_id = U.user_id
    """
    cursor.execute(query)
    results = cursor.fetchall()

    return render_template('all_albums.html', albums=results)


""" View a particular album (also public; guests can view these) """
@app.route('/albums/view/<int:album_id>', methods=["GET"])
def view_album(album_id: int):
    query = """
    SELECT A.album_name, concat(U.first_name, ' ', U.last_name) as name
    FROM Albums A JOIN Users U ON A.owner_id = U.user_id
    WHERE A.album_id = {0}
    """.format(album_id)
    results = cursor.execute(query)
    album = cursor.fetchone()
    album_name = album[0]
    uploader = album[1]

    query = """
    SELECT img_data, caption, picture_id
    FROM Pictures
    WHERE album_id = {0}
    """.format(album_id)
    results = cursor.execute(query)
    photos = cursor.fetchall()
    if len(photos) > 0:
        return render_template('view_album.html', album_title=album_name,
                               photos=photos, uploader=uploader, base64=base64)
    else:
        # displays a message that the album is empty
        return render_template('view_album.html', album_title=album_name,
                               empty=True, uploader=uploader)


@flask_login.login_required
@app.route('/albums/delete/')
def delete_album_show_form():
    """ Show a form to allow the user to select an album to delete. """
    uid = getUserIdFromEmail(flask_login.current_user.id)
    query = """
    SELECT *
    FROM Albums
    WHERE owner_id = {0}
    """.format(uid)

    cursor.execute(query)
    albums = cursor.fetchall()

    if len(albums) > 0:
        return render_template('delete-album.html', albums=albums)
    else:
        message = "You have no albums to delete"
        return render_template('delete-album.html', empty=True,
                               message=message)


@flask_login.login_required
@app.route('/albums/delete/<int:album_id>', methods=['POST'])
def delete_album(album_id):
    """
    Delete a user's album.

    Parameters:
    album_id: the ID of the album to delete
    """
    # get IDs of all pictures in this album
    query = """
    SELECT picture_id
    FROM Pictures
    WHERE album_id = {0}
    """.format(album_id)

    cursor.execute(query)
    pictures = cursor.fetchall()

    for id in pictures:
        # batch mode on --- don't show confirmation page after each deletion
        delete_photo(id[0], True)

    # now we can delete the album itself
    query = """
    DELETE FROM Albums
    WHERE album_id = {0}
    """.format(album_id)

    cursor.execute(query)
    conn.commit()

    message = "Album deleted!"
    return render_template('hello.html', message=message)


################################################################################
#                              End album methods                               #
################################################################################


################################################################################


################################################################################
#                           Social features methods                            #
################################################################################
@app.route('/top-users')
def top_users():
    # Popular_users is a view defined in the schema file.  It is already set up
    # with the things we want, so we should grab everything from it
    query = """
    SELECT *
    FROM Popular_users
    """
    cursor.execute(query)
    users = cursor.fetchall()

    return render_template('top-users.html', users=users)


def get_friends(uid, get_names=False):
    """
    Return IDs of friends of the user with the given UID.

    Parameters:
    uid: ID of the user whose friends are to be found
    get_names: whether to also return friends' names
    """

    if get_names:
        # In the subquery, we have to check for friendship in both directions
        # to make sure we get everyone
        query = """
        SELECT user_id, concat(first_name, ' ', last_name) as name
        FROM Users
        WHERE user_id IN (
          SELECT F.user_id2
          FROM Friends F
          WHERE F.user_id1 = {0}
          UNION
          SELECT F2.user_id1
          FROM Friends F2
          WHERE F2.user_id2 = {0}
        )
        """.format(uid, uid)
        cursor.execute(query)
        friends = cursor.fetchall()
        return friends
    else:
        query = """
        SELECT user_id
        FROM Users
        WHERE user_id IN (
          SELECT F.user_id2
          FROM Friends F
          WHERE F.user_id1 = {0}
          UNION
          SELECT F2.user_id1
          FROM Friends F2
          WHERE F2.user_id2 = {0}
        )
        """.format(uid, uid)
        cursor.execute(query)
        friends = cursor.fetchall()
        return friends


@flask_login.login_required
@app.route('/friends/')
def show_friends():
    """ Show the current user's friends. """
    uid = getUserIdFromEmail(flask_login.current_user.id)
    # we want to show the friends' name, hence True
    friends = get_friends(uid, True)
    empty = False

    if len(friends) == 0:
        return render_template('my_friends.html', empty=True)
    else:
        return render_template('my_friends.html', friends=friends)


@flask_login.login_required
@app.route('/friends/find')     # let a user find people to befriend
def find_friends():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    # first condition in WHERE prevents self-friending; second condition
    # prevents re-friending
    query = """
    SELECT concat(first_name, ' ', last_name), user_id
    FROM Users
    WHERE user_id != {0} AND user_id NOT IN (
      SELECT F.user_id2
      FROM Friends F
      WHERE F.user_id1 = {0}
      UNION
      SELECT F2.user_id1
      FROM Friends F2
      WHERE F2.user_id2 = {0}
    )
    """.format(uid, uid, uid)
    cursor.execute(query)
    users = cursor.fetchall()

    if len(users) == 0:
        message = "You're already friends with everyone on Photoshare!"
        return render_template('find_friends.html',
                               empty=True,
                               message=message)
    else:
        return render_template('find_friends.html', users=users)


@flask_login.login_required
@app.route('/friends/recommended')
def show_friend_recommendations():
    """
    Show friend recommendations to the user based on their current friends.
    """
    uid = getUserIdFromEmail(flask_login.current_user.id)

    # find ids of current user's friends
    my_friend_ids = get_friends(uid, False)

    # structure for tracking how many times a recommended friend is found;
    # more times == higher recommendation
    frequency_dict = {}
    for id in my_friend_ids:
        # get the ids only, because we'll get the names in one step at the end
        friends_of_friend = get_friends(id[0], False)

        for fr in friends_of_friend:
            if fr[0] == uid or fr in my_friend_ids:
                # is the supposed friend-of-a-friend me or already friends with
                # me?  If so, skip
                continue
            if fr[0] in frequency_dict:
                # id encountered --- increase recommendation score
                frequency_dict[fr[0]] += 1
            else:
                # new id, start at 1
                frequency_dict[fr[0]] = 1

    # just to make sure the list is ordered from most-recommended to
    # least-recommended
    ordered_recs = sorted(frequency_dict.items(),
                          key=itemgetter(1), reverse=True)
    recs = []
    for rec in ordered_recs:
        # now we get everyone's names
        query = """
        SELECT concat(first_name, ' ', last_name)
        FROM Users
        WHERE user_id = {0}
        """.format(rec[0])
        cursor.execute(query)
        name = cursor.fetchone()[0]
        recs.append((rec[0], name))

    return render_template('friend_recommendations.html',
                           recs=recs)


@flask_login.login_required
@app.route('/friends/add/<int:uid>', methods=['POST'])
def add_friend(uid):
    """
    Create a friendship relation between the current user and some user B

    Parameters:
    uid: the user ID of the user to befriend
    """
    current_user = getUserIdFromEmail(flask_login.current_user.id)
    if uid == current_user:
        # user is trying to befriend themselves, so deny request
        return render_template('hello.html',
                               message="You can't be friends with yourself.")
    # valid request, create record
    query = """
    INSERT INTO Friends (user_id1, user_id2)
    VALUES ({0}, {1})
    """.format(current_user, uid)
    cursor.execute(query)
    conn.commit()

    query = """
    SELECT concat(first_name, ' ', last_name) as Name
    FROM Users
    WHERE user_id = {0}
    """.format(uid)
    cursor.execute(query)
    friend = cursor.fetchone()[0]

    message = "You are now friends with {0}".format(friend)

    return render_template('hello.html',
                           message=message)
################################################################################
#                         End social features methods                          #
################################################################################


#default page
@app.route("/", methods=['GET'])
def hello():
    return render_template('hello.html', message='Welecome to Photoshare')


if __name__ == "__main__":
    #this is invoked when in the shell  you run
    #$ python app.py
    app.run(port=5000, debug=True)
