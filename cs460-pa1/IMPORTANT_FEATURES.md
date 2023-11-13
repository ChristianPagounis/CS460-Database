# IMPORTANT FEATURES

## Purpose
This file lists important features (backend and frontend) of our application
that we mustn't forget to implement, including certain assumptions mentioned in
our first deliverable.

## Features (Check off with 'x's in the box when done)
- [x] Make sure users can't comment on their own photos
- [x] Make sure users can't befriend someone they're already friends with
  - If user 1 is friends with user 2 [(1, 2) in the Friends table], an insertion
    of (2, 1) should be rejected, because, semantically (logically) those tuples
    are the same.  However, in SQL, they are considered identical.  This leaves
    it to Python to check
