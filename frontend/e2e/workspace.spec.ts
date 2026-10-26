import { test, expect } from '@playwright/test';
const session = {authenticated:true,subject_id:41,service_id:13,capabilities:['overview'],
  csrf_token:'synthetic-csrf-token',overview:{label:'Synthetic hosting',domain:'site.example',
  next_due_date:'2026-12-01',usage:null}};

test.beforeEach(async ({page}) => {
  await page.route('**/api/csrf/',route=>route.fulfill({json:{csrf_token:'synthetic-csrf-token'}}));
});
for (const width of [360,390,768,1440]) {
  test(`overview and modules fit ${width}px`, async ({page}) => {
    await page.setViewportSize({width,height:900});
    await page.route('**/api/session/',route=>route.fulfill({json:session}));
    await page.goto('/');
    await expect(page.getByRole('heading',{name:'Hosting overview'})).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await page.goto('/modules/files/');
    await expect(page.getByRole('heading',{name:'File manager',exact:true})).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    for (const slug of ['websites', 'domains', 'integrations']) {
      await page.goto(`/modules/${slug}/`);
      await expect(page.locator('#main-content h1')).toBeVisible();
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    }
  });
}
test('initial entitlement outage still allows CSRF protected logout',async({page})=>{
  await page.route('**/api/session/',route=>route.fulfill({status:503,json:{authenticated:false}}));
  let posted=false;
  await page.route('**/auth/logout/',route=>{
    posted=route.request().method()==='POST' && route.request().headers()['x-csrftoken']==='synthetic-csrf-token';
    return route.fulfill({status:200,body:''});
  });
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Unable to verify access'})).toBeVisible();
  await page.getByRole('button',{name:'Sign out'}).click();
  await expect.poll(()=>posted).toBe(true);
});
test('denied entitlement exposes no service data',async({page})=>{
  await page.route('**/api/session/',route=>route.fulfill({status:403,json:{authenticated:false}}));
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Hosting access is unavailable'})).toBeVisible();
  await expect(page.getByText('Synthetic hosting')).toHaveCount(0);
});

test('logout refreshes a token invalidated after initial page load',async({page})=>{
  let rotated=false;
  let accepted=false;
  await page.route('**/api/csrf/',route=>route.fulfill({json:{csrf_token:rotated?'fresh-token':'old-token'}}));
  await page.route('**/api/session/',route=>route.fulfill({json:{...session,csrf_token:'old-token'}}));
  await page.route('**/auth/logout/',route=>{
    accepted=route.request().headers()['x-csrftoken']==='fresh-token';
    return route.fulfill({status:accepted?200:403,body:''});
  });
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Hosting overview'})).toBeVisible();
  rotated=true;
  await page.getByRole('button',{name:'Sign out'}).click();
  await expect.poll(()=>accepted).toBe(true);
});

test('manual website upload stays visible and never claims a deployment',async({page})=>{
  await page.route('**/api/session/',route=>route.fulfill({json:session}));
  await page.goto('/modules/websites/');
  await expect(page.getByText('Upload website files')).toBeVisible();
  await page.locator('input[type=file]').setInputFiles({
    name:'my-static-site.zip',mimeType:'application/zip',
    buffer:Buffer.from('placeholder-bytes'),
  });
  await expect(page.getByRole('button',{name:'Publish website (coming soon)'})).toBeDisabled();
  await expect(page.getByText('my-static-site.zip',{exact:false})).toBeVisible();
  await expect(page.getByText('Archive validated — not published')).toHaveCount(0);
});

test('File Manager has browsable example tree but never fabricates server contents',async({page})=>{
  await page.route('**/api/session/',route=>route.fulfill({json:session}));
  await page.route('**/api/files/list/**',route=>route.fulfill({
    status:503,json:{connected:false,error:'Not connected'}
  }));
  await page.setViewportSize({width:390,height:860});
  await page.goto('/modules/files/');
  await expect(page.getByRole('heading',{name:'File manager',exact:true})).toBeVisible();
  await expect(page.getByText('Server folders are not connected yet')).toBeVisible();
  await expect(page.getByRole('button',{name:'public_html'})).toHaveCount(0);
  await page.getByRole('button',{name:'Example preview'}).click();
  await expect(page.getByText('Example preview — not your server')).toBeVisible();
  await page.getByRole('button',{name:'public_html'}).first().click();
  await expect(page.getByRole('button',{name:'index.html'})).toBeVisible();
  await expect(page.getByRole('button',{name:'assets'}).first()).toBeVisible();
  await page.getByRole('button',{name:'index.html'}).click();
  await expect(page.getByText('Example only')).toBeVisible();
  await expect(page.getByRole('button',{name:'Rename'})).toBeDisabled();
  await expect(page.getByRole('button',{name:'Delete'})).toBeDisabled();
  await expect(page.getByRole('link',{name:'Open website upload'})).toHaveAttribute('href','/modules/websites/');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.getByRole('button',{name:'My server files'}).click();
  await expect(page.getByText('Server folders are not connected yet')).toBeVisible();
  await expect(page.getByRole('button',{name:'public_html'})).toHaveCount(0);
});
