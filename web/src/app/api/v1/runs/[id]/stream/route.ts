import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const backendBase = process.env.BACKEND_URL || "http://127.0.0.1:8001";
  const backendUrl = `${backendBase}/api/v1/runs/${id}/stream`;

  const lastEventId = request.headers.get("last-event-id");
  const headers: Record<string, string> = {
    Accept: "text/event-stream",
  };
  if (lastEventId) {
    headers["Last-Event-ID"] = lastEventId;
  }

  try {
    const backendRes = await fetch(backendUrl, {
      headers,
      cache: "no-store",
    });

    if (!backendRes.ok || !backendRes.body) {
      return new Response(
        `data: {"error": "Failed to connect to backend stream: ${backendRes.status}"}\n\n`,
        {
          status: backendRes.status,
          headers: {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache, no-transform",
            Connection: "keep-alive",
            "X-Accel-Buffering": "no",
          },
        }
      );
    }

    return new Response(backendRes.body, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (err: any) {
    return new Response(
      `data: {"error": "Backend stream error: ${err.message}"}\n\n`,
      {
        status: 502,
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache, no-transform",
          Connection: "keep-alive",
        },
      }
    );
  }
}
