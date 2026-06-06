-- Bảng theo dõi job backend xử lý ảnh
create table if not exists public.poster_jobs (
  id uuid primary key default gen_random_uuid(),
  job_type text not null,
  status text not null default 'pending',
  input_json jsonb not null,
  result_json jsonb,
  error_message text,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Bảng lưu lịch sử output poster final
create table if not exists public.poster_outputs (
  id uuid primary key default gen_random_uuid(),
  template_id uuid references public.poster_templates(id),
  job_id uuid references public.poster_jobs(id),
  employee_name text,
  team_name text,
  award_title text,
  output_url text not null,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now()
);

create index if not exists idx_poster_jobs_status on public.poster_jobs(status);
create index if not exists idx_poster_jobs_created_at on public.poster_jobs(created_at desc);
create index if not exists idx_poster_outputs_created_at on public.poster_outputs(created_at desc);

alter table public.poster_jobs enable row level security;
alter table public.poster_outputs enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'poster_jobs' and policyname = 'poster_jobs_select_own_or_admin'
  ) then
    create policy "poster_jobs_select_own_or_admin"
    on public.poster_jobs
    for select
    using (
      created_by = auth.uid()
      or exists (
        select 1 from public.profiles p
        where p.id = auth.uid() and p.role = 'admin'
      )
    );
  end if;
end $$;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public' and tablename = 'poster_outputs' and policyname = 'poster_outputs_select_own_or_admin'
  ) then
    create policy "poster_outputs_select_own_or_admin"
    on public.poster_outputs
    for select
    using (
      created_by = auth.uid()
      or exists (
        select 1 from public.profiles p
        where p.id = auth.uid() and p.role = 'admin'
      )
    );
  end if;
end $$;

-- Backend dùng service_role sẽ bypass RLS, nên không cần policy insert/update riêng.
