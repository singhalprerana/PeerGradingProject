PRAGMA foreign_keys = ON;


create table if not exists entries (
  id integer primary key autoincrement,
  title text references users(username) on delete cascade,
  text text not null,
  time text not null
);

create table if not exists users (
  username text primary key,
  password text,
  authorization text CHECK(authorization in ('student','instructor','admin'))
 );

create table if not exists tasks (
  taskname text primary key,
  weight integer not null,
  creator text references users(username) on delete cascade
 );

create table if not exists grades (
  taskname text references tasks(taskname) on delete cascade,
  grader references users(username) on delete cascade,
  receiver references users(username) on delete cascade,
  grades text not null,
  review text,
  constraint grades_pk primary key (taskname, grader, receiver) 
 );

create table if not exists student_task (
  student text references users(username) on delete cascade,
  taskname text references tasks(taskname) on delete cascade, 
  constraint st_pk primary key (student, taskname)
 );

