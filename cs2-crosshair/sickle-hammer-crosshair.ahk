#Requires AutoHotkey v2.0
#SingleInstance Force

; Прицел ☭ поверх CS2: прозрачное окно с картинкой точно в центре экрана.
; Скрипт ничего не делает с процессом игры: не читает её память и не нажимает клавиши.
; F10 — показать/скрыть, Ctrl+F10 — выйти.

Size := 65        ; 49, 65 или 97 — размер картинки в пикселях
OffsetX := 0      ; сдвиг в пикселях, если центр не совпал (вправо +, влево -)
OffsetY := 0      ; (вниз +, вверх -)

ImageFile := A_ScriptDir "\sickle-hammer-" Size ".png"
if !FileExist(ImageFile) {
    MsgBox "Не найден файл картинки:`n" ImageFile
    ExitApp
}

; Цвет 010101 становится прозрачным; края картинки сливаются с чёрной обводкой.
; +E0x20 — окно пропускает клики мыши насквозь в игру.
Overlay := Gui("+AlwaysOnTop -Caption +ToolWindow -DPIScale +E0x20")
Overlay.BackColor := "010101"
Overlay.MarginX := 0
Overlay.MarginY := 0
Overlay.AddPicture("x0 y0 w" Size " h" Size, ImageFile)

X := (A_ScreenWidth - Size) // 2 + OffsetX
Y := (A_ScreenHeight - Size) // 2 + OffsetY
Overlay.Show("x" X " y" Y " w" Size " h" Size " NoActivate")
WinSetTransColor("010101", Overlay)
Visible := true

; Игра в окне без рамки иногда перекрывает оверлей — раз в секунду поднимаем его наверх.
SetTimer(KeepOnTop, 1000)

KeepOnTop() {
    if Visible
        WinSetAlwaysOnTop(1, Overlay)
}

ToggleOverlay() {
    global Visible
    Visible := !Visible
    if Visible
        Overlay.Show("NoActivate")
    else
        Overlay.Hide()
}

F10::ToggleOverlay()
^F10::ExitApp()
