import QtQuick
import QtQuick.Controls

// The pointer owner stays alive while the preview rebuilds marker delegates.
MouseArea {
    id: surface
    objectName: "timelineTimingSurface"
    property var stripView
    property real savedLeft: 0
    property real savedSpan: 1
    property real savedWidth: 1
    property real pressX: 0
    property real grabOffset: 0
    property real clickTime: 0
    property string targetKind: ""
    property int targetIndex: -1
    property string targetEdge: ""
    property bool armed: false
    property bool moved: false
    enabled: !studio.busy
    hoverEnabled: true
    cursorShape: armed ? Qt.SizeHorCursor : Qt.ArrowCursor
    function pick(x,y) {
        const lane=Math.floor(y/25)
        const rows=lane===1 ? (stripView.strip.freezes || []) : lane===2 ? (stripView.strip.slow || []) : []
        // Last painted row wins when points overlap, matching its visible order.
        for (let i=rows.length-1;i>=0;--i) {
            const row=rows[i]
            if (lane===1 && Math.abs(x-stripView.pixel(row.at))<=9)
                return {kind:row.kind,index:row.index,edge:row.index>=0 ? "at" : "",at:row.at}
            if (lane===2) {
                const a=stripView.pixel(row.sourceFrom), b=stripView.pixel(row.sourceTo)
                if (Math.abs(x-a)<=7 || Math.abs(x-b)<=7) {
                    const edge=Math.abs(x-a)<=Math.abs(x-b) ? "from" : "to"
                    return {kind:row.kind,index:row.index,edge:edge,at:edge==="from" ? row.sourceFrom : row.sourceTo}
                }
                if(x>=stripView.pixel(row.at) && x<=stripView.pixel(row.end))
                    return {kind:row.kind,index:row.index,edge:"",at:row.sourceFrom}
            }
        }
        return null
    }
    function moveTo(x) {
        if (!armed || !stripView.controller.dragging) return
        if (Math.abs(x-pressX)>3) moved=true
        if (moved) {
            const at=savedLeft+Math.max(0,Math.min(savedWidth,x-grabOffset))/savedWidth*savedSpan
            stripView.controller.preview(at)
        }
    }
    onPressed: function(mouse) {
        const hit=pick(mouse.x,mouse.y)
        if (!hit || stripView.controller.dragging || studio.markup.drawing) { mouse.accepted=false; return }
        forceActiveFocus()
        targetKind=hit.kind; targetIndex=hit.index; targetEdge=hit.edge; clickTime=hit.at
        savedLeft=stripView.strip.left; savedSpan=stripView.strip.right-savedLeft; savedWidth=width
        pressX=mouse.x; grabOffset=mouse.x-stripView.pixel(hit.at); moved=false
        armed=targetEdge!=="" && stripView.controller.beginTiming(targetKind,targetIndex,targetEdge)
        if (targetEdge!=="" && !armed) mouse.accepted=false
    }
    onPositionChanged: function(mouse) { if(pressed) moveTo(mouse.x) }
    onReleased: function(mouse) {
        if (armed) {
            const valid=stripView.controller.dragging
            moveTo(mouse.x)
            if (valid && moved) stripView.controller.commit()
            else if (valid) { stripView.controller.cancel(); studio.seek(clickTime) }
        } else if (targetKind!=="") studio.seek(clickTime)
        armed=false
    }
    onDoubleClicked: {
        if (armed) stripView.controller.cancel()
        armed=false
        stripView.controller.editPoint(targetKind,targetIndex,clickTime)
    }
    onCanceled: { if(armed) stripView.controller.cancel(); armed=false }
    ToolTip.visible: containsMouse && mouseY>=25 && mouseY<75 && !pressed
    ToolTip.text: "Drag a manual freeze or either slow-motion edge. Double-click to edit. Escape cancels."
}
