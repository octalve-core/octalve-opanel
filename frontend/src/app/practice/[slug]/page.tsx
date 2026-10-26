import {notFound} from 'next/navigation';
import {catalog} from '@/features/practice/catalog';
import {PracticeWorkspace} from '@/features/practice/PracticeWorkspace';
export default async function Page({params}:{params:Promise<{slug:string}>}){const {slug}=await params;if(!catalog[slug]&&slug!=='activity')notFound();return <PracticeWorkspace slug={slug}/>;}
