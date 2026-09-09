import QtQuick

MouseArea {
    id: surface
    objectName: "markupSurface"
    property var workspace
    property var hostViewport
    property var hostFrame
    property real lastX: 0
    property real lastY: 0
    property bool panning: false
    enabled: studio.duration>0 && !studio.busy
    cursorShape: panning ? Qt.ClosedHandCursor : studio.markup.tool==="pan" ? Qt.OpenHandCursor : Qt.CrossCursor
    onPressed: function(mouse) {
        forceActiveFocus()
        var pos=mapToItem(hostViewport,mouse.x,mouse.y)
        lastX=pos.x; lastY=pos.y
        panning=studio.markup.tool==="pan" || workspace.immersive
        if (!panning) studio.markup.begin(mouse.x/width,mouse.y/height)
    }
    onPositionChanged: function(mouse) {
        if (!pressed) return
        if (panning) {
            var pos=mapToItem(hostViewport,mouse.x,mouse.y)
            var maxX=Math.max(0,(hostFrame.width*workspace.zoom-hostViewport.width)/2)
            var maxY=Math.max(0,(hostFrame.height*workspace.zoom-hostViewport.height)/2)
            workspace.panX=Math.max(-maxX,Math.min(maxX,workspace.panX+pos.x-lastX))
            workspace.panY=Math.max(-maxY,Math.min(maxY,workspace.panY+pos.y-lastY))
            lastX=pos.x; lastY=pos.y
        } else if (studio.markup.drawing) studio.markup.update(mouse.x/width,mouse.y/height)
    }
    onReleased: function(mouse) {
        if (!panning && studio.markup.drawing) {
            studio.markup.update(mouse.x/width,mouse.y/height)
            studio.markup.commit()
        }
        panning=false
    }
    onCanceled: { panning=false; studio.markup.cancel() }
    onWheel: function(wheel) {
        if (!studio.markup.drawing) workspace.zoomTo(workspace.zoom+(wheel.angleDelta.y>0 ? .2 : -.2))
    }
}
