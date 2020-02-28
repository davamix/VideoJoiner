# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['VideoJoiner.py'],
             pathex=['F:\\Development\\UnicosGaming\\VideoJoiner'],
             binaries=[],
             datas=[('input\\intro.mov', 'input'), 
                    ('input\\outro.mov', 'input'), 
                    ('tools', 'tools'),
                    ('images\\256x256.ico', 'images'),
                    ('images\\256x256.png', 'images'),
                    ('resources\\about_content.html', 'resources')],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='UG Clips',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          icon='images/256x256.ico' )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='UG Clips')
