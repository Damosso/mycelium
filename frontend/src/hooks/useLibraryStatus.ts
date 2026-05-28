import { useQuery } from '@tanstack/react-query';
import { api } from '../api';

export function useLibraryStatus(): Record<string, string> {
  const { data } = useQuery({
    queryKey: ['library-status-map'],
    queryFn: api.libraryStatusMap,
    staleTime: 30_000,
  });
  return data || {};
}
