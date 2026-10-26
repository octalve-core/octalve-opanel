import { notFound } from "next/navigation";
import { Workspace } from "@/components/Workspace";
import { findModule } from "@/lib/modules";
export const dynamic = "force-dynamic";
export default async function ModulePage({ params }: { params: Promise<{slug:string}> }) {
  const {slug} = await params;
  if (!findModule(slug) || slug === "overview") notFound();
  return <Workspace selected={slug} />;
}
