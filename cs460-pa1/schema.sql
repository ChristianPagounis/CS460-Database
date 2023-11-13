-- IMPORTANT: THE FOLLOWING LINE IS FOR DEV PURPOSES ONLY
--            AND SHOULD BE REMOVED BEFORE SUBMISSION
DROP DATABASE IF EXISTS photoshare;


CREATE DATABASE IF NOT EXISTS photoshare;
USE photoshare;
DROP TABLE IF EXISTS Pictures CASCADE;
DROP TABLE IF EXISTS Users CASCADE;

-- ############################# Entity tables #################################

CREATE TABLE Users (
  user_id int unsigned AUTO_INCREMENT,
  email varchar(255) UNIQUE,
  password_hash varchar(100),
  first_name varchar(20),
  last_name varchar(20),
  gender enum('male', 'female', 'other'),
  dob date,
  hometown varchar(100),
  contrib_score int unsigned,
  CONSTRAINT users_pk PRIMARY KEY (user_id)
);

CREATE TABLE Albums
(
  album_id int unsigned AUTO_INCREMENT PRIMARY KEY,
  owner_id int unsigned NOT NULL,
  album_name varchar(255),
  creation_date date,
  FOREIGN KEY(owner_id) REFERENCES Users(user_id)
);

CREATE TABLE Pictures
(
  picture_id int unsigned AUTO_INCREMENT,
  album_id int unsigned NOT NULL,
  owner_id int unsigned NOT NULL,
  img_data longblob,
  caption VARCHAR(255),
  CONSTRAINT pictures_pk PRIMARY KEY (picture_id),
  FOREIGN KEY(album_id) REFERENCES Albums(album_id) ON DELETE CASCADE,
  FOREIGN KEY(owner_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

CREATE TABLE Friends
(
  user_id1 int unsigned NOT NULL,
  user_id2 int unsigned NOT NULL,
  PRIMARY KEY (user_id1, user_id2),
  FOREIGN KEY (user_id1) REFERENCES Users(user_id),
  FOREIGN KEY (user_id2) REFERENCES Users(user_id)
);

CREATE TABLE Comments
(
  comment_id int unsigned AUTO_INCREMENT PRIMARY KEY,
  author_id int unsigned NOT NULL,
  picture_id int unsigned,
  post_date date,
  text TEXT NOT NULL,
  FOREIGN KEY(picture_id) REFERENCES Pictures(picture_id) ON DELETE CASCADE,
  FOREIGN KEY(author_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

CREATE TABLE Tags
(
  tag_id int unsigned AUTO_INCREMENT PRIMARY KEY,
  tag_text text NOT NULL
);

-- ########################## Relationship Tables ##############################

-- Pictures are tagged with tags
CREATE TABLE Tagged_with
(
  picture_id int unsigned,
  tag_id int unsigned,
  FOREIGN KEY(picture_id) REFERENCES Pictures(picture_id),
  FOREIGN KEY(tag_id) REFERENCES Tags(tag_id),
  PRIMARY KEY(picture_id, tag_id)
);

-- Users can like pictures
CREATE TABLE Likes
(
  user_id int unsigned,
  picture_id int unsigned,
  FOREIGN KEY(user_id) REFERENCES Users(user_id),
  FOREIGN KEY(picture_id) REFERENCES Pictures(picture_id),
  PRIMARY KEY(user_id, picture_id) -- users cannot like a picture more than once
);

-- ################################ Triggers ###################################

-- Increment user's contribution score when they upload a photo
DELIMITER //
CREATE TRIGGER addPhotoContribution
AFTER INSERT ON Pictures
FOR EACH ROW
BEGIN
  UPDATE Users
  SET contrib_score = contrib_score + 1
  WHERE Users.user_id = NEW.owner_id;
END; //
DELIMITER ;

-- Decrement user's contribution score when they delete a photo
DELIMITER //
CREATE TRIGGER removePhotoContribution
AFTER DELETE ON Pictures
FOR EACH ROW
BEGIN
  UPDATE Users
  SET contrib_score = contrib_score - 1
  WHERE Users.user_id = OLD.owner_id;
END; //
DELIMITER ;

-- Increment user's contribution score when they comment
DELIMITER //
CREATE TRIGGER addCommentContribution
AFTER INSERT ON Comments
FOR EACH ROW
BEGIN
  UPDATE Users
  SET contrib_score = contrib_score + 1
  WHERE Users.user_id = NEW.author_id;
END; //
DELIMITER ;

-- Decrement user's contribution score when their comments are deleted
DELIMITER //
CREATE TRIGGER deleteCommentContribution
AFTER DELETE ON Comments
FOR EACH ROW
BEGIN
  UPDATE Users
  SET contrib_score = contrib_score - 1
  WHERE Users.user_id = OLD.author_id;
END; //
DELIMITER ;

-- Ensure a user cannot somehow end up friends with themselves
DELIMITER //
CREATE TRIGGER noFriendsWithSelf
BEFORE INSERT ON Friends
FOR EACH ROW
BEGIN
  IF NEW.user_id1 = NEW.user_id2 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'A user may not be friends with themselves.';
  END IF;
END; //
DELIMITER ;

-- Ensure a user can't befriend someone they're already friends with
DELIMITER //
CREATE TRIGGER checkFriendExists
BEFORE INSERT ON Friends
FOR EACH ROW
BEGIN
  IF EXISTS (SELECT * FROM Friends WHERE user_id1 = NEW.user_id1 AND user_id2 = NEW.user_id2) THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'You are already friends with this user.';
  ELSEIF EXISTS (SELECT * FROM Friends WHERE user_id1 = NEW.user_id2 AND user_id2 = NEW.user_id1) THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'You are already friends with this user.';
  END IF;
END; //
DELIMITER ;

-- ################################# Views #####################################
CREATE VIEW Popular_users AS
SELECT user_id, CONCAT(first_name, " ", last_name) AS name, contrib_score
FROM Users
ORDER BY contrib_score DESC
LIMIT 10
