#!/usr/bin/env python3
# Remap ELAN stylus BTN_TOOL_RUBBER (321) -> BTN_STYLUS2 (middle-ish) or BTN_STYLUS (right-ish)
# while preventing GNOME/libinput from ever seeing BTN_TOOL_RUBBER (so it can't switch to eraser tool).
#
# - Auto-detect ALL /dev/input/event* with vid/pid 04f3:43f4 that advertise BTN_TOOL_RUBBER.
# - Grab them all (exclusive) so libinput stops seeing the real events.
# - Create ONE virtual tablet device and forward all pen motion/pressure/tilt/buttons to it.
# - Suppress BTN_TOOL_RUBBER and replace it with a tablet button.
# - Suppress BTN_TOOL_PEN=0 while rubber is held (hardware often toggles tools PEN<->RUBBER).

from evdev import InputDevice, UInput, ecodes, util
import sys
import time
import select
import traceback

VID = 0x04F3
PID = 0x43F4

# Choose mapping:
#   BTN_STYLUS2 is commonly interpreted as "middle click" in many stacks/apps.
#   BTN_STYLUS is commonly interpreted as "right click".
RUBBER_TO = ecodes.BTN_STYLUS2  # change to ecodes.BTN_STYLUS for right click


def dev_has_key(dev: InputDevice, keycode: int) -> bool:
    caps = dev.capabilities().get(ecodes.EV_KEY, [])
    return keycode in caps


def absinfo_or_none(dev: InputDevice, code: int):
    try:
        return dev.absinfo(code)
    except Exception:
        return None


def find_sources():
    sources = []
    for path in util.list_devices():
        try:
            d = InputDevice(path)
        except Exception:
            continue
        try:
            if d.info.vendor != VID or d.info.product != PID:
                continue
        except Exception:
            continue
        if dev_has_key(d, ecodes.BTN_TOOL_RUBBER):
            sources.append(d)
    return sources


def build_virtual_caps(primary: InputDevice):
    keys = set(primary.capabilities().get(ecodes.EV_KEY, []))

    # Ensure common stylus/tablet keys exist
    keys.add(ecodes.BTN_TOOL_PEN)
    keys.add(ecodes.BTN_TOUCH)
    keys.add(ecodes.BTN_STYLUS)
    keys.add(ecodes.BTN_STYLUS2)

    # Remove eraser-tool switch
    keys.discard(ecodes.BTN_TOOL_RUBBER)

    # Ensure replacement exists
    keys.add(RUBBER_TO)

    abs_list = []
    for code in (ecodes.ABS_X, ecodes.ABS_Y, ecodes.ABS_PRESSURE, ecodes.ABS_TILT_X, ecodes.ABS_TILT_Y):
        ai = absinfo_or_none(primary, code)
        if ai is not None:
            abs_list.append((code, ai))

    return {
        ecodes.EV_KEY: sorted(keys),
        ecodes.EV_ABS: abs_list,
    }


def code_name(code: int) -> str:
    # BTN map covers BTN_*; KEY covers KEY_*.
    return ecodes.BTN.get(code) or ecodes.KEY.get(code) or str(code)


def main():
    sources = find_sources()
    if not sources:
        print("[-] No ELAN 04f3:43f4 devices advertising BTN_TOOL_RUBBER were found.", file=sys.stderr)
        print("[-] Devices seen:", file=sys.stderr)
        for p in util.list_devices():
            try:
                d = InputDevice(p)
                print(f"  {p}: {d.name} (vid={getattr(d.info,'vendor',0):04x} pid={getattr(d.info,'product',0):04x})")
            except Exception:
                pass
        sys.exit(1)

    # Prefer a node named "Stylus" as primary for abs ranges/caps
    primary = next((d for d in sources if "Stylus" in (d.name or "")), sources[0])

    print("[+] Sources to grab (all advertise BTN_TOOL_RUBBER):")
    for d in sources:
        print(f"    - {d.path}: {d.name} (vid={d.info.vendor:04x} pid={d.info.product:04x})")

    caps = build_virtual_caps(primary)
    virt_name = "ELAN Stylus (remapped no-eraser)"
    ui = UInput(caps, name=virt_name, bustype=primary.info.bustype)
    print(f"[+] Created virtual tablet: {virt_name}")

    # Grab all sources
    for d in sources:
        try:
            d.grab()
        except Exception as e:
            print(f"[-] Failed to grab {d.path} ({d.name}): {e}", file=sys.stderr)
            ui.close()
            sys.exit(1)

    print("[+] Grabbed all source devices (GNOME/libinput should not see real eraser tool now)")
    print(f"[*] Remap: BTN_TOOL_RUBBER -> {code_name(RUBBER_TO)} (Ctrl+C to stop)")

    rubber_held = False
    pen_in_prox = False

    fd_to_dev = {d.fd: d for d in sources}
    fds = list(fd_to_dev.keys())

    try:
        while True:
            r, _, _ = select.select(fds, [], [], 1.0)
            if not r:
                continue

            for fd in r:
                dev = fd_to_dev[fd]
                for e in dev.read():
                    # PEN proximity handling
                    if e.type == ecodes.EV_KEY and e.code == ecodes.BTN_TOOL_PEN:
                        # Suppress PEN=0 while rubber is held
                        if rubber_held and e.value == 0:
                            continue
                        pen_in_prox = (e.value == 1)
                        ui.write_event(e)
                        continue

                    # RUBBER handling: suppress tool switch and emit replacement button
                    if e.type == ecodes.EV_KEY and e.code == ecodes.BTN_TOOL_RUBBER:
                        rubber_held = (e.value == 1)

                        # Keep PEN in proximity
                        if rubber_held and not pen_in_prox:
                            ui.write(ecodes.EV_KEY, ecodes.BTN_TOOL_PEN, 1)
                            pen_in_prox = True

                        ui.write(ecodes.EV_KEY, RUBBER_TO, 1 if rubber_held else 0)
                        ui.syn()
                        continue

                    # Forward everything else (ABS motion/pressure/tilt, BTN_TOUCH, BTN_STYLUS, BTN_STYLUS2, etc.)
                    try:
                        ui.write_event(e)
                    except OSError:
                        pass

    except KeyboardInterrupt:
        pass
    except Exception:
        traceback.print_exc()
    finally:
        for d in sources:
            try:
                d.ungrab()
            except Exception:
                pass
            try:
                d.close()
            except Exception:
                pass
        try:
            ui.close()
        except Exception:
            pass


if __name__ == "__main__":
    time.sleep(0.2)
    main()

