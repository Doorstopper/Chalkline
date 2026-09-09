import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: timeline
    objectName: "clipTimeline"
    property var controller: studio.clipTimeline
    property var strip: controller.model
    spacing: 4
    visible: strip.start !== undefined
    function clock(t) { return Number(t || 0).toFixed(1) + "s" }
    function pixel(t) { return (Number(t || 0)-(strip.left || 0))/Math.max(.001,(strip.right || 1)-(strip.left || 0))*track.width }
    Label { text: "CLIP TIMELINE   " + timeline.clock(timeline.strip.start) + " — " + timeline.clock(timeline.strip.end); color: "#9DAFC2"; font.pixelSize: 11 }
    RowLayout {
        Layout.fillWidth: true; spacing: 6
        Column {
            Layout.preferredWidth: 48
            Repeater { model: ["Trim", "Freeze", "Slow", "Draw"]
                Label { required property string modelData; text: modelData; height: 25; color: "#9DAFC2"; font.pixelSize: 10 }
            }
        }
        Rectangle {
            id: track
            objectName: "clipTimelineTrack"
            Layout.fillWidth: true; Layout.preferredHeight: 100
            color: "#111B27"; radius: 5; clip: true
            MouseArea {
                anchors.fill: parent; enabled: !studio.busy && !timeline.controller.dragging
                onClicked: function(mouse) { forceActiveFocus(); studio.seek(timeline.strip.left + mouse.x/width*(timeline.strip.right-timeline.strip.left)) }
            }
            Repeater { model: 3
                Rectangle { required property int index; x: 0; y: (index+1)*25; width: track.width; height: 1; color: "#2C3543" }
            }
            Rectangle { x: timeline.pixel(timeline.strip.start); y: 3; width: Math.max(1,timeline.pixel(timeline.strip.end)-x); height: 19; color: "#4A5664" }
            Rectangle { x: timeline.pixel(timeline.strip.tag); y: 0; width: 1; height: 100; color: "#83909D"; opacity: .6 }
            Repeater {
                model: [{edge:"start"}, {edge:"end"}]
                Rectangle {
                    required property var modelData
                    objectName: "trim-" + modelData.edge
                    x: timeline.pixel(timeline.strip[modelData.edge])-6; y: 0; width: 12; height: 25; radius: 3; color: "#FF795E"
                    Accessible.name: "Trim " + modelData.edge
                    MouseArea {
                        anchors.fill: parent; enabled: !studio.busy; cursorShape: Qt.SizeHorCursor
                        property real savedLeft: 0
                        property real savedSpan: 1
                        property real savedWidth: 1
                        property real offset: 0
                        function move(mouse) {
                            if (!timeline.controller.dragging) return
                            const x = Math.max(0, Math.min(savedWidth, mapToItem(track,mouse.x,mouse.y).x-offset))
                            timeline.controller.preview(savedLeft+x/savedWidth*savedSpan)
                        }
                        onPressed: function(mouse) {
                            forceActiveFocus()
                            savedLeft=timeline.strip.left; savedSpan=timeline.strip.right-savedLeft; savedWidth=track.width
                            offset=mapToItem(track,mouse.x,mouse.y).x-timeline.pixel(timeline.strip[modelData.edge])
                            if (!timeline.controller.begin(modelData.edge)) mouse.accepted=false
                        }
                        onPositionChanged: function(mouse) { if (pressed) move(mouse) }
                        onReleased: function(mouse) { move(mouse); timeline.controller.commit() }
                        onCanceled: timeline.controller.cancel()
                        ToolTip.visible: containsMouse; hoverEnabled: true
                        ToolTip.text: "Drag to trim " + modelData.edge + "; Escape cancels"
                    }
                }
            }
            Repeater {
                model: [ {rows: timeline.strip.freezes || [], lane:1, color:"#FFB376"},
                         {rows: timeline.strip.slow || [], lane:2, color:"#73BBD1"},
                         {rows: timeline.strip.marks || [], lane:3, color:"#B5A4DC"} ]
                Item {
                    id: lane
                    required property var modelData
                    width: track.width; height: 25; y: modelData.lane*25
                    Repeater {
                        model: lane.modelData.rows
                        Rectangle {
                            id: marker
                            required property var modelData
                            objectName: "timing-"+modelData.kind+"-"+modelData.index
                            x: timeline.pixel(modelData.at)-3; y: 5
                            width: Math.max(7,timeline.pixel(modelData.end)-timeline.pixel(modelData.at)); height: 15
                            color: lane.modelData.color; radius: 3
                            opacity: modelData.active ? 1 : .3
                            MouseArea {
                                anchors.fill: parent; hoverEnabled: true
                                enabled: modelData.kind==="markup" && !studio.busy && !timeline.controller.dragging
                                onClicked: { forceActiveFocus(); studio.seek(modelData.at) }
                                onDoubleClicked: timeline.controller.editPoint(modelData.kind,modelData.index,modelData.at)
                                ToolTip.visible: containsMouse
                                ToolTip.text: modelData.label + " · " + timeline.clock(modelData.at) + (modelData.active ? "" : " · outside clip") + " · double-click to select"
                            }
                            Repeater {
                                model: marker.modelData.kind==="slow" ? ["from","to"] : []
                                Rectangle {
                                    required property string modelData
                                    readonly property real sourceTime: modelData==="from" ? marker.modelData.sourceFrom : marker.modelData.sourceTo
                                    visible: sourceTime>=timeline.strip.left && sourceTime<=timeline.strip.right
                                    x: timeline.pixel(sourceTime)-marker.x-4
                                    y: -3; width: 8; height: 21; radius: 2
                                    color: "#B3E5EF"
                                }
                            }
                        }
                    }
                }
            }
            Rectangle { x: timeline.pixel(studio.position); y: 0; width: 2; height: 100; color: "#8FC4FF" }
            TimelineTimingSurface { anchors.fill: parent; stripView: timeline }
        }
    }
    Flow {
        Layout.fillWidth: true; Layout.preferredHeight: implicitHeight; spacing: 4
        Repeater {
            model: [{label:"Start −0.5s",edge:"start",delta:-.5}, {label:"Start +0.5s",edge:"start",delta:.5},
                    {label:"End −0.5s",edge:"end",delta:-.5}, {label:"End +0.5s",edge:"end",delta:.5}]
            ActionButton { required property var modelData; text: modelData.label; font.pixelSize: 10
                enabled: !studio.busy && !timeline.controller.dragging
                onClicked: timeline.controller.nudge(modelData.edge,modelData.delta)
            }
        }
    }
    Shortcut { sequence: "Escape"; enabled: timeline.controller.dragging; onActivated: timeline.controller.cancel() }
}
