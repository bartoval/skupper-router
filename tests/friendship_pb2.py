# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: friendship.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='friendship.proto',
  package='',
  syntax='proto3',
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n\x10\x66riendship.proto\"6\n\x06Person\x12\r\n\x05\x65mail\x18\x01 \x01(\t\x12\x0c\n\x04name\x18\x02 \x01(\t\x12\x0f\n\x07\x66riends\x18\x03 \x03(\t\"0\n\x0c\x43reateResult\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t\"\x1c\n\x0bPersonEmail\x12\r\n\x05\x65mail\x18\x01 \x01(\t\"5\n\x13\x43ommonFriendsResult\x12\x0f\n\x07\x66riends\x18\x01 \x03(\t\x12\r\n\x05\x63ount\x18\x02 \x01(\x05\"3\n\x11\x46riendshipRequest\x12\x0e\n\x06\x65mail1\x18\x01 \x01(\t\x12\x0e\n\x06\x65mail2\x18\x02 \x01(\t\"W\n\x12\x46riendshipResponse\x12\x18\n\x07\x66riend1\x18\x01 \x01(\x0b\x32\x07.Person\x12\x18\n\x07\x66riend2\x18\x02 \x01(\x0b\x32\x07.Person\x12\r\n\x05\x65rror\x18\x03 \x01(\t2\xd6\x01\n\nFriendship\x12\"\n\x06\x43reate\x12\x07.Person\x1a\r.CreateResult\"\x00\x12(\n\x0bListFriends\x12\x0c.PersonEmail\x1a\x07.Person\"\x00\x30\x01\x12<\n\x12\x43ommonFriendsCount\x12\x0c.PersonEmail\x1a\x14.CommonFriendsResult\"\x00(\x01\x12<\n\x0bMakeFriends\x12\x12.FriendshipRequest\x1a\x13.FriendshipResponse\"\x00(\x01\x30\x01\x62\x06proto3'
)




_PERSON = _descriptor.Descriptor(
  name='Person',
  full_name='Person',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='email', full_name='Person.email', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='name', full_name='Person.name', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='friends', full_name='Person.friends', index=2,
      number=3, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=20,
  serialized_end=74,
)


_CREATERESULT = _descriptor.Descriptor(
  name='CreateResult',
  full_name='CreateResult',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='success', full_name='CreateResult.success', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='message', full_name='CreateResult.message', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=76,
  serialized_end=124,
)


_PERSONEMAIL = _descriptor.Descriptor(
  name='PersonEmail',
  full_name='PersonEmail',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='email', full_name='PersonEmail.email', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=126,
  serialized_end=154,
)


_COMMONFRIENDSRESULT = _descriptor.Descriptor(
  name='CommonFriendsResult',
  full_name='CommonFriendsResult',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='friends', full_name='CommonFriendsResult.friends', index=0,
      number=1, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='count', full_name='CommonFriendsResult.count', index=1,
      number=2, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=156,
  serialized_end=209,
)


_FRIENDSHIPREQUEST = _descriptor.Descriptor(
  name='FriendshipRequest',
  full_name='FriendshipRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='email1', full_name='FriendshipRequest.email1', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='email2', full_name='FriendshipRequest.email2', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=211,
  serialized_end=262,
)


_FRIENDSHIPRESPONSE = _descriptor.Descriptor(
  name='FriendshipResponse',
  full_name='FriendshipResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='friend1', full_name='FriendshipResponse.friend1', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='friend2', full_name='FriendshipResponse.friend2', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='error', full_name='FriendshipResponse.error', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=264,
  serialized_end=351,
)

_FRIENDSHIPRESPONSE.fields_by_name['friend1'].message_type = _PERSON
_FRIENDSHIPRESPONSE.fields_by_name['friend2'].message_type = _PERSON
DESCRIPTOR.message_types_by_name['Person'] = _PERSON
DESCRIPTOR.message_types_by_name['CreateResult'] = _CREATERESULT
DESCRIPTOR.message_types_by_name['PersonEmail'] = _PERSONEMAIL
DESCRIPTOR.message_types_by_name['CommonFriendsResult'] = _COMMONFRIENDSRESULT
DESCRIPTOR.message_types_by_name['FriendshipRequest'] = _FRIENDSHIPREQUEST
DESCRIPTOR.message_types_by_name['FriendshipResponse'] = _FRIENDSHIPRESPONSE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Person = _reflection.GeneratedProtocolMessageType('Person', (_message.Message,), {
  'DESCRIPTOR' : _PERSON,
  '__module__' : 'friendship_pb2'
  # @@protoc_insertion_point(class_scope:Person)
  })
_sym_db.RegisterMessage(Person)

CreateResult = _reflection.GeneratedProtocolMessageType('CreateResult', (_message.Message,), {
  'DESCRIPTOR' : _CREATERESULT,
  '__module__' : 'friendship_pb2'
  # @@protoc_insertion_point(class_scope:CreateResult)
  })
_sym_db.RegisterMessage(CreateResult)

PersonEmail = _reflection.GeneratedProtocolMessageType('PersonEmail', (_message.Message,), {
  'DESCRIPTOR' : _PERSONEMAIL,
  '__module__' : 'friendship_pb2'
  # @@protoc_insertion_point(class_scope:PersonEmail)
  })
_sym_db.RegisterMessage(PersonEmail)

CommonFriendsResult = _reflection.GeneratedProtocolMessageType('CommonFriendsResult', (_message.Message,), {
  'DESCRIPTOR' : _COMMONFRIENDSRESULT,
  '__module__' : 'friendship_pb2'
  # @@protoc_insertion_point(class_scope:CommonFriendsResult)
  })
_sym_db.RegisterMessage(CommonFriendsResult)

FriendshipRequest = _reflection.GeneratedProtocolMessageType('FriendshipRequest', (_message.Message,), {
  'DESCRIPTOR' : _FRIENDSHIPREQUEST,
  '__module__' : 'friendship_pb2'
  # @@protoc_insertion_point(class_scope:FriendshipRequest)
  })
_sym_db.RegisterMessage(FriendshipRequest)

FriendshipResponse = _reflection.GeneratedProtocolMessageType('FriendshipResponse', (_message.Message,), {
  'DESCRIPTOR' : _FRIENDSHIPRESPONSE,
  '__module__' : 'friendship_pb2'
  # @@protoc_insertion_point(class_scope:FriendshipResponse)
  })
_sym_db.RegisterMessage(FriendshipResponse)



_FRIENDSHIP = _descriptor.ServiceDescriptor(
  name='Friendship',
  full_name='Friendship',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_start=354,
  serialized_end=568,
  methods=[
  _descriptor.MethodDescriptor(
    name='Create',
    full_name='Friendship.Create',
    index=0,
    containing_service=None,
    input_type=_PERSON,
    output_type=_CREATERESULT,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='ListFriends',
    full_name='Friendship.ListFriends',
    index=1,
    containing_service=None,
    input_type=_PERSONEMAIL,
    output_type=_PERSON,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='CommonFriendsCount',
    full_name='Friendship.CommonFriendsCount',
    index=2,
    containing_service=None,
    input_type=_PERSONEMAIL,
    output_type=_COMMONFRIENDSRESULT,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
  _descriptor.MethodDescriptor(
    name='MakeFriends',
    full_name='Friendship.MakeFriends',
    index=3,
    containing_service=None,
    input_type=_FRIENDSHIPREQUEST,
    output_type=_FRIENDSHIPRESPONSE,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
])
_sym_db.RegisterServiceDescriptor(_FRIENDSHIP)

DESCRIPTOR.services_by_name['Friendship'] = _FRIENDSHIP

# @@protoc_insertion_point(module_scope)
