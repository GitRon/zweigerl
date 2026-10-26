// Drags a scroll container with the mouse held down (#100): the tree canvas in <c-tree.canvas>.
//
// datastar has no attribute for this: a drag is state across pointerdown, pointermove and pointerup, it has
// to tell a click from a drag by distance, and it has to swallow the click a drag ends with - none of which
// fits an inline expression. See docs/patterns/datastar.md, "When JavaScript of our own is allowed".
//
// Any element with "data-drag-scroll" takes part; the listeners sit on the document, so a container that
// datastar patches in later needs nothing. Dragging changes the container's scroll position and nothing
// else, so zoom, the scrollbars, the keyboard and "scrollIntoView" never learn it happened. While a drag is
// running the container carries data-drag-scroll="dragging", which the template styles.

// Below this distance a press is a click, so a card still opens its person card.
const THRESHOLD = 5;

let drag = null;

document.addEventListener("pointerdown", (event) => {
    if (event.pointerType !== "mouse" || event.button !== 0) return;
    const container = event.target.closest("[data-drag-scroll]");
    if (!container) return;
    // A press on the container's own scrollbars belongs to the scrollbars.
    const box = container.getBoundingClientRect();
    if (
        event.clientX - box.left >= container.clientLeft + container.clientWidth ||
        event.clientY - box.top >= container.clientTop + container.clientHeight
    ) {
        return;
    }
    drag = {
        container,
        pointerId: event.pointerId,
        x: event.clientX,
        y: event.clientY,
        left: container.scrollLeft,
        top: container.scrollTop,
        moving: false,
    };
});

document.addEventListener("pointermove", (event) => {
    if (!drag || event.pointerId !== drag.pointerId) return;
    const dx = event.clientX - drag.x;
    const dy = event.clientY - drag.y;
    if (!drag.moving) {
        if (Math.hypot(dx, dy) < THRESHOLD) return;
        drag.moving = true;
        // Captured only now: captured on the press, the click of a plain press would go to the container.
        drag.container.setPointerCapture(drag.pointerId);
        drag.container.dataset.dragScroll = "dragging";
        window.getSelection()?.removeAllRanges();
    }
    // "instant", or the container's smooth scrolling trails behind the mouse.
    drag.container.scrollTo({ left: drag.left - dx, top: drag.top - dy, behavior: "instant" });
});

// The click a drag ends with did not mean the card under the mouse.
const swallow = (event) => {
    event.stopPropagation();
    event.preventDefault();
};

const end = (event) => {
    if (!drag || event.pointerId !== drag.pointerId) return;
    if (drag.moving) {
        drag.container.dataset.dragScroll = "";
        // The click follows the pointerup in the same task; released over another element, none follows,
        // so the listener goes again after this task and the next real click is not lost.
        if (event.type === "pointerup") {
            window.addEventListener("click", swallow, { capture: true, once: true });
            setTimeout(() => window.removeEventListener("click", swallow, { capture: true }), 0);
        }
    }
    drag = null;
};

document.addEventListener("pointerup", end);
document.addEventListener("pointercancel", end);
