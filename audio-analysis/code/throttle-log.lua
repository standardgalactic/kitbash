-- throttle-log.lua
--
-- Logs every volume, mute and pause change in mpv against movie time,
-- plus a manual marker key, to a CSV beside the video file.
--
-- Install: copy into mpv's scripts folder
--   Windows: %APPDATA%\mpv\scripts\
--   Linux:   ~/.config/mpv/scripts/
--
-- During viewing, control volume ONLY in mpv (9 / 0, mouse wheel, m to
-- mute). Leave the Windows master volume and the amp at fixed settings.
-- Press Shift+A to drop a marker when something bothers you but you
-- don't touch the volume.
--
-- mpv's volume slider is cubic: amplitude = (vol/100)^3, so the gain
-- column is 60*log10(vol/100) dB relative to 100%.

local utils = require "mp.utils"

local log = nil
local started = false

local function now_pos()
    return mp.get_property_number("time-pos", -1)
end

local function gain_db(vol)
    if vol == nil or vol <= 0 then return -120 end
    return 60 * math.log(vol / 100) / math.log(10)
end

local function write(event, value)
    if not log then return end
    local vol = mp.get_property_number("volume", -1)
    log:write(string.format("%s,%.3f,%.3f,%s,%s,%.1f,%s,%s\n",
        os.date("!%Y-%m-%dT%H:%M:%SZ"),
        os.clock(),
        now_pos(),
        event,
        tostring(value),
        vol,
        string.format("%.2f", gain_db(vol)),
        tostring(mp.get_property_bool("mute", false))))
    log:flush()
end

mp.register_event("file-loaded", function()
    local path = mp.get_property("path", "")
    local dir, name = utils.split_path(path)
    local stamp = os.date("%Y%m%d-%H%M%S")
    local out = utils.join_path(dir, name .. ".throttle-" .. stamp .. ".csv")
    log = io.open(out, "w")
    if not log then
        mp.osd_message("throttle-log: cannot write " .. out, 5)
        return
    end
    log:write("utc,clock_s,movie_s,event,value,volume,gain_db,muted\n")
    started = true
    write("START", mp.get_property("audio-params/channel-count", "?"))
    mp.osd_message("throttle-log: recording", 2)
end)

mp.observe_property("volume", "number", function(_, v)
    if started then write("VOLUME", v) end
end)

mp.observe_property("mute", "bool", function(_, v)
    if started then write("MUTE", v) end
end)

mp.observe_property("pause", "bool", function(_, v)
    if started then write("PAUSE", v) end
end)

mp.add_key_binding("A", "throttle-mark", function()
    write("MARK", "")
    mp.osd_message("marked", 0.7)
end)

mp.register_event("end-file", function()
    write("END", "")
    if log then log:close() end
    log = nil
    started = false
end)
