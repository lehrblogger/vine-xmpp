#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import logging
from constants import g

if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    raw_input = input
    
class NotUserException(Exception):
    pass

class AbstractUser(object):
    def __init__(self, name=None, dbid=None):
        self._noted_vinebot_ids = None
    
    def status(self):
        return g.ectl.user_status(self.name)
    
    def is_online(self):
        return self.user_status() != 'unavailable'  # this function is useful for list filterss
    
    def fetch_visible_active_vinebots(self):
        return g.db.execute_and_fetchall("""SELECT participants.vinebot_id
                                            FROM edges AS outgoing, edges AS incoming, participants
                                            WHERE outgoing.vinebot_id = incoming.vinebot_id
                                            AND outgoing.from_id = %(id)s
                                            AND incoming.to_id = %(id)s
                                            AND outgoing.to_id = incoming.from_id
                                            AND participants.user_id = outgoing.to_id
                                         """, {
                                            'id': self.id
                                         }, strip_pairs=True)
    
    def note_visible_active_vinebots(self):
        self._noted_vinebot_ids = set(self.fetch_visible_active_vinebots())
    
    def update_visible_active_vinebots(self):
        if self._noted_vinebot_ids == None:
            raise Exception, 'User\'s noted visible active vinebots must be fetched before they are updated!'
        current_vinebot_ids = set(self.fetch_visible_active_vinebots())
        for vinebot_id in self._noted_vinebot_ids.difference(current_vinebot_ids):
            vinebot = DatabaseVinebot(g.db, g.ectl, dbid=reverse_edge.vinebot_id)
            g.ectl.delete_rosteritem(self.name, vinebot.jiduser)
        for vinebot_id in current_vinebot_ids.difference(self._noted_vinebot_ids):
            vinebot = DatabaseVinebot(g.db, self.ectl, dbid=reverse_edge.vinebot_id)
            g.ectl.add_rosteritem(self.name, vinebot.jiduser, vinebot.jiduser)  #TODO calculate nick
        self._noted_vinebot_ids = None
    
    def get_active_vinebots(self):
        vinebot_ids = g.db.execute_and_fetchall("""SELECT vinebot_id
                                                   FROM participants
                                                   WHERE user_id = %(id)s
                                                   LIMIT 1
                                                """, {
                                                   'id': self.id
                                                }, strip_pairs=True)
        return [DatabaseVinebot(g.db, g.ectl, dbid=vinebot_id) for vinebot_id in vinebot_ids]
    
    def delete(self):
        g.db.execute("""DELETE FROM users
                        WHERE id = %(id)s
                     """, {
                        'id': self.id
                     })
        g.ectl.unregister(self.name)
    
    def __eq__(self, other):
        if not isinstance(other, User):
            return False
    
        return (self.id == other.id and self.name == other.name)
    

class InsertedUser(AbstractUser):
    def __init__(self, name, password):
        super(InsertedUser, self).__init__()
        dbid = g.db.execute("""INSERT INTO users (name)
                               VALUES (%(name)s)
                            """, {
                               'name': name
                            })
        g.ectl.register(name, password)
        self.id = dbid
        self.name = name
    

class FetchedUser(AbstractUser):
    def __init__(self, name=None, dbid=None):
        super(FetchedUser, self).__init__()
        if name and dbid:
            self.id = dbid
            self.name = name
        elif name:
            dbid = g.db.execute_and_fetchall("""SELECT id
                                                    FROM users
                                                    WHERE name = %(name)s
                                                 """, {
                                                    'name': name
                                                 }, strip_pairs=True)
            self.id = dbid[0] if len(dbid) == 1 else None
            self.name = name
        elif dbid:
            name = g.db.execute_and_fetchall("""SELECT name
                                                         FROM users
                                                         WHERE id = %(id)s
                                                      """, {
                                                         'id': dbid
                                                      }, strip_pairs=True)
            self.id   = dbid
            self.name = name[0] if len(name) == 1 else None
        else:
            raise Exception, 'User objects must be initialized with either a name or id.'
        if not self.id or not self.name:
            raise NotUserException, 'both of these users were not found in the database.'
    
