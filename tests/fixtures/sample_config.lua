local vars = require("sample_variables")

hl.config({
    general = {
        layout = "dwindle",
        gaps_in = vars.gapsIn,
        border_size = 2,
    },

    decoration = {
        rounding = 10,
    },
})

hl.env("XCURSOR_SIZE", "24")
hl.env("XCURSOR_THEME", vars.cursorTheme)

hl.monitor({
    output = "",
    mode = "preferred",
    scale = 1,
})

hl.exec_cmd("waybar")
hl.exec_cmd("hyprpaper")
