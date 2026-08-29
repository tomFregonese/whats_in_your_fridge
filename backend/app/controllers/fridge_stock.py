import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.dependencies import get_fridge_stock_service
from app.dto.fridge_stock_dto import (
    DictationParseDtoIn,
    FridgeStockBulkAddDtoIn,
    FridgeStockItemDtoIn,
    FridgeStockItemDtoOut,
    FridgeStockMergeDtoIn,
    MergeDismissalDtoIn,
    MergeSuggestionDtoOut,
)
from app.services.fridge_stock_service import FridgeStockService

router = APIRouter(prefix="/fridge-stock", tags=["fridge-stock"])


@router.get("")
def list_fridge_stock(
    service: FridgeStockService = Depends(get_fridge_stock_service),
) -> list[FridgeStockItemDtoOut]:
    return [FridgeStockItemDtoOut.from_domain(item) for item in service.list_items()]


@router.post("", status_code=201)
def add_fridge_stock_item(
    dto: FridgeStockItemDtoIn,
    service: FridgeStockService = Depends(get_fridge_stock_service),
) -> FridgeStockItemDtoOut:
    return FridgeStockItemDtoOut.from_domain(service.add_item(dto.to_domain()))


@router.patch("/{item_id}")
def update_fridge_stock_item(
    item_id: int,
    dto: FridgeStockItemDtoIn,
    service: FridgeStockService = Depends(get_fridge_stock_service),
) -> FridgeStockItemDtoOut:
    return FridgeStockItemDtoOut.from_domain(service.update_item(item_id, dto.to_domain()))


@router.delete("/{item_id}", status_code=204)
def delete_fridge_stock_item(
    item_id: int,
    service: FridgeStockService = Depends(get_fridge_stock_service),
) -> None:
    service.remove_item(item_id)


@router.post("/bulk", status_code=201)
def bulk_add_fridge_stock_items(
    dto: FridgeStockBulkAddDtoIn,
    service: FridgeStockService = Depends(get_fridge_stock_service),
) -> list[FridgeStockItemDtoOut]:
    """Commits the reviewed/edited result of a dictation pass (see
    `POST /dictation` below) — updates a same-name existing item instead of
    duplicating it (see `FridgeStockService.upsert_dictated_items`)."""
    items = [item.to_domain() for item in dto.items]
    return [
        FridgeStockItemDtoOut.from_domain(item)
        for item in service.upsert_dictated_items(items)
    ]


@router.post("/dictation")
def stream_dictation(
    dto: DictationParseDtoIn,
    service: FridgeStockService = Depends(get_fridge_stock_service),
) -> StreamingResponse:
    """Streams the transcribe-then-structure pipeline for a dictated audio
    clip as SSE events (`transcribing` / `transcribed` / `items` / `error`
    / `done` — see `app/dictation_streaming_service.py` for the exact
    shapes) rather than blocking for one big JSON response: even though
    both stages are local and fast now (no more OpenRouter round trip —
    see `agent/dictation.py`), this still gives the user visible progress
    for the ~1-4s wait instead of a static spinner.

    Deliberately a plain `def`, not `async def`: FastAPI already runs a
    sync route handler in its own thread pool, so the blocking
    `service.parse_dictation_stream(...)` generator below never touches
    the event loop. Persists nothing — the frontend reviews the final
    `items` event and commits via `POST /bulk`.
    """
    events = service.parse_dictation_stream(dto.audio_base64, dto.audio_format)

    def event_stream() -> Iterator[str]:
        for event in events:
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/merge-suggestions")
def list_merge_suggestions(
    service: FridgeStockService = Depends(get_fridge_stock_service),
) -> list[MergeSuggestionDtoOut]:
    """Fridge-stock names the local model thinks name the same real
    ingredient (translation, typo, singular/plural — see
    `agent/duplicate_check.py`), minus anything already dismissed.
    Recomputed on every call — nothing here is persisted. The frontend
    calls this on its own schedule (page load, after any mutation); it's
    never part of the plain `GET ""` list."""
    return [MergeSuggestionDtoOut.from_domain(s) for s in service.find_merge_suggestions()]


@router.post("/merge")
def merge_fridge_stock_items(
    dto: FridgeStockMergeDtoIn,
    service: FridgeStockService = Depends(get_fridge_stock_service),
) -> FridgeStockItemDtoOut:
    return FridgeStockItemDtoOut.from_domain(
        service.merge_items(
            keep_id=dto.keep_item_id, remove_id=dto.remove_item_id, merged_name=dto.merged_name
        )
    )


@router.post("/merge-suggestions/dismiss", status_code=204)
def dismiss_merge_suggestion(
    dto: MergeDismissalDtoIn,
    service: FridgeStockService = Depends(get_fridge_stock_service),
) -> None:
    service.dismiss_merge_suggestion(dto.name_a, dto.name_b)
