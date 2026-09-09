import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: playback
    objectName: "playbackPanel"
    property var workspace
    property bool expanded: false
    spacing: 5
    Slider {
        Layout.fillWidth: true
        from: 0; to: Math.max(1,studio.duration); value: studio.position
        enabled: studio.duration>0
        onMoved: studio.seek(value)
    }
    RowLayout {
        Layout.fillWidth: true
        ActionButton { text: studio.playing ? "Pause" : "Play"; onClicked: studio.togglePlay() }
        ActionButton { text: "‹ Frame"; onClicked: studio.stepButton(-1) }
        ActionButton { text: "Frame ›"; onClicked: studio.stepButton(1) }
        Text { text: workspace.clock(studio.position); color: "#F3F0E8"; font.family: "Consolas"; Layout.fillWidth: true }
        ActionButton { text: "−"; onClicked: workspace.zoomTo(workspace.zoom-.25) }
        ActionButton { text: Math.round(workspace.zoom*100)+"%"; onClicked: workspace.zoomTo(1) }
        ActionButton { text: "+"; onClicked: workspace.zoomTo(workspace.zoom+.25) }
    }
    RowLayout {
        visible: !workspace.immersive
        ComboBox {
            model: ["0.1×", "0.25×", "0.5×", "1×", "1.5×", "2×", "3×"]
            currentIndex: [.1,.25,.5,1,1.5,2,3].indexOf(studio.playbackRate)
            onActivated: studio.setRate([.1,.25,.5,1,1.5,2,3][currentIndex])
        }
        ActionButton { text: studio.muted ? "Unmute" : "Mute"; onClicked: studio.mute() }
        Item { Layout.fillWidth: true }
        ActionButton { text: expanded ? "Less" : "More"; onClicked: expanded = !expanded }
        ActionButton { text: "Review edited clip"; enabled: studio.selection>=0; onClicked: studio.review() }
    }
    Popup {
        visible: !workspace.immersive && expanded
        onClosed: playback.expanded = false
        width: Math.min(520, playback.width)
        height: Math.min(280, details.implicitHeight + topPadding + bottomPadding)
        y: -height - 5
        clip: true
        ScrollView {
            anchors.fill: parent
            contentWidth: availableWidth
            ColumnLayout {
                id: details
                width: parent.width
                spacing: 4
                Flow {
                    visible: !workspace.immersive && expanded; Layout.fillWidth: true; Layout.preferredHeight: implicitHeight; spacing: 4
                    Repeater {
                        model: [-20,-10,-5,-1,1,5,10,20]
                        ActionButton {
                            required property int modelData
                            text: (modelData>0 ? "+" : "")+modelData+"s"
                            enabled: studio.duration>0; onClicked: studio.skip(modelData)
                        }
                    }
                }
                Flow {
                    visible: !workspace.immersive && expanded; Layout.fillWidth: true; Layout.preferredHeight: implicitHeight; spacing: 4
                    ActionButton { text: "Previous clip"; enabled: studio.clipRows.length>0; onClicked: studio.navigateClip(-1) }
                    ActionButton { text: "Next clip"; enabled: studio.clipRows.length>0; onClicked: studio.navigateClip(1) }
                    ActionButton { text: studio.bookmark>=0 ? "★ Spot" : "☆ Spot"; enabled: studio.duration>0; onClicked: studio.markSpot() }
                    ActionButton { text: "Resume" + (studio.bookmark>=0 ? " "+workspace.clock(studio.bookmark) : ""); enabled: studio.bookmark>=0 && studio.duration>0; onClicked: studio.resumeSpot() }
                }
                
                Flow {
                    visible: !workspace.immersive && expanded
                    Layout.fillWidth: true; Layout.preferredHeight: implicitHeight; spacing: 4
                    RowLayout {
                        ActionButton { text: "Start"; enabled: studio.selection>=0; onClicked: studio.restartClip() }
                        ActionButton { text: "Close clip"; enabled: studio.selection>=0; onClicked: studio.closeClip() }
                    }
                    CheckBox { text: "Loop clip"; checked: studio.loopEnabled; onClicked: studio.toggleLoop() }
                    ActionButton { text: "Next markup point"; enabled: studio.selection>=0; onClicked: studio.nextMarkup() }
                    ActionButton { text: "Play on — this clip"; enabled: studio.selection>=0; onClicked: studio.playOn(false) }
                    ActionButton { text: "Play on — last clip"; enabled: studio.clips.length>0; onClicked: studio.playOn(true) }
                }
            }
        }
    }
}
