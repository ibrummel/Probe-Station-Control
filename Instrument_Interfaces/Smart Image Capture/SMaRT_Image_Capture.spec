# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['SMaRT_Image_Capture.py'],
             pathex=['C:\\Users\\Public\\Ian Data\\EIS\\SMaRT Image Capture', 'C:\\SMaRT_Image_Capture'],
             binaries=[],
             datas=[],
             hiddenimports=['cv2'],
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
          a.binaries,
          a.zipfiles,
          a.datas,
          [],
          name='SMaRT_Image_Capture',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True )
