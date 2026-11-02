[app]

title = Tito Match3
package.name = titomatch3
package.domain = org.tito
p4a.branch = v2022.12.20

source.dir = .
source.include_exts = py,png,jpg,jpeg,mp3,json,ttf

version = 2.1

requirements = python3,pygame,requests,gtts,click

orientation = portrait
fullscreen = 1

android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
