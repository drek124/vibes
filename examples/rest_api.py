"""REST-only usage with `PassiveClient` - no WebSocket, no events.

Good for scripts, cron jobs and dashboards that just need data from the API.

Run with:
    python examples/rest_api.py
"""
import os
import asyncio

import vibes

TOKEN = os.environ["VIBES_TOKEN"]


async def main():
    api = vibes.PassiveClient(token=TOKEN)
    try:
        # --- Your own application ------------------------------------------
        app = await api.fetch_client()
        print(f"Owner: {app.owner} ({app.owner.url})")
        print(f"Rate limit: {app.rate_limit}")
        if app.webhook:
            print(f"Webhook: {app.webhook.url} (scope={app.webhook.scope}, active={app.webhook.active})")

        # --- Live streams ---------------------------------------------------
        # `limit` maxes out at 100. `mature=False` keeps 18+ streams out of the
        # results; leaving it at the default requests them (403 if your account
        # isn't 18+). `category` takes a slug such as "chit-chat".
        streams = await api.fetch_streams(limit=5, mature=False)
        for stream in streams:
            print(f"{stream.channel} | {stream.title} | {stream.viewers} viewers "
                  f"| {stream.category.name} | live for {round(stream.duration / 60, 1)}min")

        # A Stream can also be used to talk back to its chat, no socket needed.
        if streams:
            await streams[0].chat.send("Hello from a REST client!")

        # Narrowing by category:
        podcast_streams = await api.fetch_streams(category="podcasts", limit=3)
        print(f"{len(podcast_streams)} podcast(s) live")

        # --- Users ----------------------------------------------------------
        # Accepts a username or an ID. Cached for 90s to save API calls.
        user = await api.fetch_user("some-streamer")

        if user is None:
            print("That user doesn't exist.")
        else:
            print(f"{user.username} - {user.followers} followers")
            print(f"  bio: {user.bio}")
            print(f"  premium: {user.premium.name} (level {user.premium.level})")
            print(f"  mention: {user.mention}")
            if user.is_live and user.stream:
                print(f"  live now: {user.stream.title}")

        # --- Error handling -------------------------------------------------
        # 404 -> vibes.errors.NotFound, 403 -> vibes.errors.Forbidden,
        # anything else non-OK -> httpx.HTTPStatusError.
        # 429 responses are retried automatically after the Retry-After header.
        try:
            missing = await api.fetch_user("a-user-that-does-not-exist-xyz")
            print("unexpectedly found:", missing)
        except vibes.NotFound:
            print("user not found (NotFound)")

        try:
            await api.fetch_streams(mature=True)
        except vibes.Forbidden:
            print("this account isn't allowed to see mature streams")

        # --- Custom requests ------------------------------------------------
        # Every endpoint method is built on send_request, so you can call
        # endpoints the library doesn't wrap yet. Paths are relative to
        # https://backend.vibes.stream/api/v1/.
        response = await api.send_request(
            api.client.get,
            "streams/live",
            params={"limit": 1},
            raise_for_status=False,  # get the raw response instead of raising
        )
        print(f"raw request -> {response.status_code}")
        print(response.json()["data"][0]["title"])

        # --- Cache ----------------------------------------------------------
        api.clear_cache()  # drop cached users & messages
    finally:
        await api.close()


asyncio.run(main())
