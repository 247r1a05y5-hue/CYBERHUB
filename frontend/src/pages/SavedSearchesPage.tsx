import React, { useState } from "react";
import { Link } from "react-router-dom";
import { Bookmark, Search, Plus, Folder, Lock } from "lucide-react";
import { AppShell } from "../components/shell/AppShell";

export const SavedSearchesPage: React.FC = () => {
  const [collections] = useState<any[]>([]);

  return (
    <AppShell>
      <div className="p-6 max-w-6xl mx-auto w-full space-y-6 bg-[#000000] text-[#F5F5F5] min-h-[calc(100vh-3.5rem)]">
        <div className="flex items-center justify-between pb-4 border-b border-[#1A1A1A]">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-[#F5F5F5] flex items-center gap-2">
              <Bookmark className="w-5 h-5 text-[#F5F5F5]" />
              Saved Searches & Collections
            </h1>
            <p className="text-xs text-[#777777] mt-0.5">
              Curated forensic collections and bookmarked reverse-image search queries.
            </p>
          </div>
        </div>

        {collections.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Render collections */}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center p-16 text-center bg-[#080808] border border-[#1A1A1A] rounded-2xl">
            <Bookmark className="w-12 h-12 text-[#2B2B2B] mb-3" />
            <h3 className="text-sm font-semibold text-[#F5F5F5]">
              No Saved Collections
            </h3>
            <p className="text-xs text-[#777777] max-w-sm mt-1 mb-4">
              Save useful discoveries, reference images, and search queries during investigations to view them here.
            </p>
            <Link
              to="/dashboard"
              className="px-4 py-2 rounded-lg bg-[#151515] border border-[#2B2B2B] text-xs font-semibold text-[#F5F5F5] hover:bg-[#202020]"
            >
              Explore Image Search
            </Link>
          </div>
        )}
      </div>
    </AppShell>
  );
};
