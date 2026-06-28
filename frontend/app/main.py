from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from app.routers import (
    auth, dashboard, trips, my_trips, start_trip,
    settings, vehicles, community, fuel, journal, booking,
    provider,
)

app = FastAPI(title="RoadBuddy Frontend")
templates = Jinja2Templates(directory="app/templates")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(trips.router)
app.include_router(my_trips.router)
app.include_router(start_trip.router)
app.include_router(settings.router)
app.include_router(vehicles.router)
app.include_router(community.router)
app.include_router(fuel.router)
app.include_router(journal.router)
app.include_router(booking.router)
app.include_router(provider.router)


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    from app.core.config import AUTH_COOKIE_NAME
    token = request.cookies.get(AUTH_COOKIE_NAME)
    return templates.TemplateResponse(request, "landing.html", {
        "request": request,
        "is_logged_in": bool(token)
    })

