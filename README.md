HP MPP 2.0 Pen Middle-Click Fix (Ubuntu • ELAN)
=============================================

If you're reading this, you likely ran into the same issue I did: the HP MPP 2.0 pen
does not behave correctly on Ubuntu, especially when trying to use the pen buttons
for browsing or playing games like RuneScape / RuneLite.

This setup fixes that by remapping the ELAN pen’s button input at the kernel input
layer.

--------------------------------------------------------------------

What This Fix Does
-----------------

- Remaps the ELAN pen button (`BTN_TOOL_RUBBER`) to a usable mouse button
  (default: middle click)
- Works for general desktop use
- Works for games, but **requires Xorg** (Wayland has limitations)

--------------------------------------------------------------------

Requirements
------------

Install the required dependency:

```
sudo apt install -y python3-evdev
```

--------------------------------------------------------------------

Installation
------------

1) Install the script

- Download `elan-pen-middleclick.py` and move it to:
  `/usr/local/bin/elan-pen-middleclick.py`
- Make it executable:

```
sudo chmod +x /usr/local/bin/elan-pen-middleclick.py
```

--------------------------------------------------------------------

2) Create the systemd service

Create the service file:

```
sudo nano /etc/systemd/system/elan-pen-middleclick.service
```

Paste the following **exactly**:

```
[Unit]
Description=ELAN pen: remap BTN_TOOL_RUBBER to stylus button (keep pen tool)
After=graphical.target
Wants=graphical.target

[Service]
Type=simple
ExecStart=/usr/local/bin/elan-pen-middleclick.py
Restart=always
RestartSec=1

[Install]
WantedBy=graphical.target
```

Save and exit.

--------------------------------------------------------------------

3) Reload systemd

```
sudo systemctl daemon-reload
```

--------------------------------------------------------------------

Testing (Recommended)
---------------------

Before enabling the service, test the script manually:

```
sudo /usr/local/bin/elan-pen-middleclick.py
```

- If everything is working, the script will run and wait for input.
- Press **Ctrl + C** to exit.
- Test the pen button while it is running.

If everything works as expected, continue below.

--------------------------------------------------------------------

Enable the Service
------------------

Start the service and enable it at boot:

```
sudo systemctl enable --now elan-pen-middleclick.service
```

Verify it is running:

```
systemctl status elan-pen-middleclick.service --no-pager
```

--------------------------------------------------------------------

Disable the Service (Optional)
------------------------------

To turn it off at any time:

```
sudo systemctl disable --now elan-pen-middleclick.service
```

--------------------------------------------------------------------

Wayland vs Xorg (Important)
---------------------------

- **Wayland**
  - Works for browsing and general desktop use
- **Xorg (X11)**
  - **Required for games**, including RuneScape / RuneLite

If you plan to game, you must log into an Xorg session.

--------------------------------------------------------------------

Troubleshooting
---------------

**Device not being grabbed**

Run:

```
sudo evtest
```

- Identify the correct event number for the ELAN pen.
- Update the event reference in `elan-pen-middleclick.py` if needed.
- Auto-detection usually works, so this is rarely required.

--------------------------------------------------------------------

Changing the Button Mapping
---------------------------

1) Edit the script:

```
sudo nano /usr/local/bin/elan-pen-middleclick.py
```

2) Replace `BTN_MIDDLE` with another button, for example:

- `BTN_RIGHT`
- `BTN_LEFT`

--------------------------------------------------------------------

Second Pen Button
-----------------

The second pen button does not require this script.

You can configure it directly in Ubuntu:
**Settings → Tablet → Pen Buttons**
