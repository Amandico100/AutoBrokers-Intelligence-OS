import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';
import { createClient } from '@supabase/supabase-js';

export const dynamic = 'force-dynamic';

const supabaseAdmin = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
  { auth: { persistSession: false } },
);

export async function GET(request: NextRequest) {
  try {
    const cookieStore = await cookies();
    const adminCookie = cookieStore.get('smith_admin_session');

    if (!adminCookie) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { searchParams } = new URL(request.url);
    const status = searchParams.get('status');
    const actionType = searchParams.get('action_type');
    const limitParam = Number(searchParams.get('limit') || '100');
    const limit = Math.min(Math.max(limitParam || 100, 1), 250);

    let query = supabaseAdmin
      .from('system_logs')
      .select(
        'id,timestamp,user_id,admin_id,company_id,action_type,resource_type,resource_id,details,ip_address,user_agent,session_id,status,error_message',
      )
      .order('timestamp', { ascending: false })
      .limit(limit);

    if (status && status !== 'all') {
      query = query.eq('status', status);
    }

    if (actionType && actionType !== 'all') {
      query = query.eq('action_type', actionType);
    }

    const { data: logs, error } = await query;

    if (error) {
      console.error('[ADMIN LOGS] Error:', error);
      return NextResponse.json({ error: 'Error fetching system logs' }, { status: 500 });
    }

    return NextResponse.json({ logs: logs || [] });
  } catch (error) {
    console.error('[ADMIN LOGS] Error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 });
  }
}
