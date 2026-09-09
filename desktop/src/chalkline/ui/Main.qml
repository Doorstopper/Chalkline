import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import Chalkline 1.0

ApplicationWindow {
    id: window
    width: 1440; height: 920
    minimumWidth: 1050; minimumHeight: 720
    visible: true
    title: "Chalkline • Desktop prototype 0.1.0"
    color: "#10151D"
    palette.window: "#10151D"
    palette.windowText: "#F3F0E8"
    palette.base: "#10151D"
    palette.text: "#F3F0E8"
    palette.button: "#253142"
    palette.buttonText: "#F3F0E8"
    palette.highlight: "#FF795E"
    palette.highlightedText: "#10151D"
    font.family: "Segoe UI"
    property bool immersive: false
    property real zoom: 1
    property real panX: 0
    property real panY: 0
    property string tool: studio.markup.tool
    property bool typing: activeFocusItem instanceof TextInput || activeFocusItem instanceof TextEdit
    onClosing: function(close) { close.accepted = studio.canClose() }

    function fullScreen() {
        immersive = !immersive
        if (immersive) showFullScreen(); else showNormal()
    }
    function zoomTo(value) {
        zoom = Math.max(1, Math.min(5, value))
        if (zoom === 1) { panX=0; panY=0 }
    }
    function clock(seconds) {
        return Math.floor(seconds/60).toString().padStart(2,"0") + ":" + (seconds%60).toFixed(2).padStart(5,"0")
    }

    Shortcut { sequence: "Space"; enabled: !window.typing; onActivated: studio.togglePlay() }
    Shortcut { sequence: "Left"; enabled: !window.typing; onActivated: studio.step(-1) }
    Shortcut { sequence: "Right"; enabled: !window.typing; onActivated: studio.step(1) }
    Shortcut { sequence: "["; enabled: !window.typing; onActivated: studio.navigateClip(-1) }
    Shortcut { sequence: "]"; enabled: !window.typing; onActivated: studio.navigateClip(1) }
    Shortcut { sequence: ","; enabled: !window.typing; onActivated: studio.stepRate(-1) }
    Shortcut { sequence: "."; enabled: !window.typing; onActivated: studio.stepRate(1) }
    Shortcut { sequence: "Ctrl+S"; onActivated: studio.save() }
    Shortcut { sequence: "Ctrl+Shift+S"; onActivated: studio.saveAs() }
    Shortcut { sequence: "Ctrl+Z"; enabled: !window.typing; onActivated: studio.undo() }
    Repeater {
        model: studio.pads
        Item {
            required property var modelData
            required property int index
            Shortcut { sequence: modelData.key; enabled: modelData.key !== "" && !window.typing && studio.duration>0 && !studio.busy; onActivated: studio.tagPad(index) }
        }
    }
    Shortcut { sequence: "Escape"; enabled: studio.markup.drawing; onActivated: studio.markup.cancel() }
    Shortcut { sequence: "F11"; onActivated: window.fullScreen() }
    Shortcut { sequence: "Escape"; enabled: !studio.clipTimeline.dragging && !studio.markup.drawing; onActivated: { if (window.immersive) window.fullScreen(); else studio.closeClip() } }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: window.immersive ? 10 : 22
        spacing: 14
        RowLayout {
            visible: !window.immersive
            Layout.fillWidth: true
            Text { text: "CHALKLINE"; font.pixelSize: 26; font.bold: true; font.letterSpacing: 2; color: "#F3F0E8" }
            Text { text: "NATIVE PROTOTYPE  /  0.1.0"; color: "#FF795E"; font.pixelSize: 11; font.letterSpacing: 1 }
            Item { Layout.fillWidth: true }
            ActionButton { text: "Open match"; enabled: !studio.busy; onClicked: studio.openVideo() }
            ActionButton { text: "Open project / JSON"; enabled: !studio.busy; onClicked: studio.openProject() }
            ActionButton { text: "Save project"; onClicked: studio.save() }
            ActionButton { text: "Save as"; onClicked: studio.saveAs() }
            ActionButton { text: "Undo"; onClicked: studio.undo() }
        }
        Rectangle { visible: !window.immersive; Layout.fillWidth: true; height: 1; color: "#2C3543" }
        RowLayout {
            visible: !window.immersive
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true; Layout.minimumWidth: 0
                Text { text: studio.mediaName; font.pixelSize: 20; font.bold: true; color: "#F3F0E8"; elide: Text.ElideMiddle; Layout.fillWidth: true; Layout.minimumWidth: 0 }
                Text { text: studio.mediaDetails; color: "#9DAFC2"; font.pixelSize: 12 }
            }
            Text { text: "Media proof of concept • full feature port pending"; color: "#9DAFC2"; font.pixelSize: 12; visible: window.width >= 1200 }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            spacing: 14
            Rectangle {
                visible: !window.immersive
                Layout.preferredWidth: 210; Layout.fillHeight: true
                color: "#19222E"; radius: 10
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 14
                    Text { text: "CLIPS  /  " + studio.clips.length; color: "#9DAFC2"; font.pixelSize: 11; font.letterSpacing: 1 }
                    ComboBox {
                        Layout.fillWidth: true; model: ["Time", "Player", "Category", "Kind"]
                        currentIndex: ["time", "player", "category", "kind"].indexOf(studio.tagSettings.sort)
                        onActivated: studio.sortClips(["time", "player", "category", "kind"][currentIndex])
                    }
                    ComboBox {
                        Layout.fillWidth: true; model: studio.playerFilters; textRole: "label"; valueRole: "value"
                        currentIndex: { var rows=studio.playerFilters; for(var i=0;i<rows.length;i++) if(rows[i].value===studio.playerFilter) return i; return -1 }
                        onActivated: studio.filterPlayer(currentValue)
                    }
                    ListView {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        clip: true; spacing: 8
                        model: studio.clipRows
                        delegate: Rectangle {
                            required property var modelData
                            required property int index
                            width: ListView.view.width; height: 104; radius: 6
                            color: modelData.id===studio.current.id ? "#344256" : "#222D3B"
                            border.width: modelData.id===studio.current.id ? 1 : 0
                            border.color: "#FF795E"
                            Column {
                                anchors.fill: parent; anchors.margins: 10; spacing: 5
                                Text { text: modelData.group; visible: text!==""; color: "#FF795E"; font.pixelSize: 10; width: parent.width; elide: Text.ElideRight }
                                Text { text: modelData.number+"  "+modelData.label; color: "#F3F0E8"; font.bold: true; width: parent.width; elide: Text.ElideRight }
                                Text { text: window.clock(modelData.displayTime)+"  ·  "+(modelData.shapes || []).length+" drawings"; color: "#9DAFC2"; font.pixelSize: 11 }
                                Text { text: modelData.playerText || "Team"; color: "#9DAFC2"; font.pixelSize: 11; width: parent.width; elide: Text.ElideRight }
                                Text { text: (modelData.kind || "") + (modelData.exported ? "  EXPORTED" : ""); color: "#73BBD1"; font.pixelSize: 9 }
                            }
                            MouseArea { anchors.fill: parent; enabled: !studio.busy; onClicked: studio.selectClipId(modelData.id) }
                        }
                    }
                    ActionButton { text: "Clear all clips"; enabled: studio.clips.length>0 && !studio.busy; Layout.fillWidth: true; onClicked: studio.clearClips() }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true; spacing: 10
                Flow {
                    visible: !window.immersive; Layout.fillWidth: true; Layout.preferredHeight: implicitHeight
                    spacing: 5
                    Repeater {
                        model: studio.pads
                        ActionButton {
                            required property var modelData
                            required property int index
                            text: (modelData.key ? modelData.key+"  " : "")+modelData.label
                            enabled: studio.duration>0 && !studio.busy
                            onClicked: { forceActiveFocus(); studio.tagPad(index) }
                        }
                    }
                    ActionButton { text: "+ Custom"; enabled: studio.duration>0 && !studio.busy; onClicked: studio.customTag() }
                    ActionButton { text: "Edit tags"; onClicked: studio.editPads() }
                }
                Flow {
                    visible: !window.immersive; Layout.fillWidth: true; Layout.preferredHeight: implicitHeight; spacing: 8
                    CheckBox { text: "Auto-edit / loop"; checked: studio.tagSettings.autoEdit; onClicked: studio.setTagSettings(studio.tagSettings.lag,checked,studio.tagSettings.player) }
                    TextField { width: 145; placeholderText: "Default player"; text: studio.tagSettings.player; onEditingFinished: studio.setTagSettings(studio.tagSettings.lag,studio.tagSettings.autoEdit,text) }
                    Label { text: "Reaction lag (s)"; height: 40; verticalAlignment: Text.AlignVCenter }
                    TextField { width: 50; text: studio.tagSettings.lag; validator: DoubleValidator { bottom: 0; top: 5 } onEditingFinished: studio.setTagSettings(Number(text),studio.tagSettings.autoEdit,studio.tagSettings.player) }
                }
                Rectangle {
                    id: viewport
                    objectName: "videoViewport"
                    Layout.fillWidth: true; Layout.fillHeight: true
                    color: "#070A0F"; clip: true; radius: 8
                    Item {
                        id: frame
                        width: Math.min(viewport.width, viewport.height*studio.aspect)
                        height: width/studio.aspect
                        x: (viewport.width-width)/2+window.panX
                        y: (viewport.height-height)/2+window.panY
                        scale: window.zoom
                        VideoOutput {
                            id: videoOutput
                            anchors.fill: parent
                            endOfStreamPolicy: VideoOutput.KeepLastFrame
                            Component.onCompleted: studio.mediaPlayer.videoOutput = videoOutput
                        }
                        AnnotationLayer {
                            anchors.fill: parent
                            dataModel: studio.markup.preview
                            sourceTime: studio.position
                            settings: studio.renderSettings
                        }
                        MarkupSurface { anchors.fill: parent; workspace: window; hostViewport: viewport; hostFrame: frame }
                    }
                    Text {
                        anchors.centerIn: parent; visible: studio.duration===0
                        text: "Your match.\nYour perspective."; color: "#F3F0E8"; font.pixelSize: 36; font.bold: true
                    }
                    ActionButton { anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 10; text: window.immersive ? "Exit fullscreen" : "Fullscreen"; onClicked: window.fullScreen() }
                }
                PlaybackPanel { workspace: window; Layout.fillWidth: true }
                ClipTimeline { Layout.fillWidth: true; visible: !window.immersive && studio.selection>=0 && studio.duration>0 }
            }
            Rectangle {
                visible: !window.immersive
                Layout.preferredWidth: 240; Layout.fillHeight: true
                color: "#19222E"; radius: 10
                ScrollView {
                    anchors.fill: parent; anchors.margins: 14; clip: true
                    contentWidth: availableWidth
                    ClipInspector { width: parent.width; workspace: window }
                }
            }
        }
        Text { text: studio.status; Layout.fillWidth: true; wrapMode: Text.WordWrap; color: "#73BBD1"; font.pixelSize: 12 }
    }
}
