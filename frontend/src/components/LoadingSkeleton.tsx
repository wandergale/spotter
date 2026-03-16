import { Skeleton, Box, Card, CardContent } from '@mui/material';

export default function LoadingSkeleton() {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {/* Map skeleton */}
      <Card>
        <Skeleton variant="rectangular" height={48} sx={{ borderRadius: 0 }} />
        <Skeleton variant="rectangular" height={400} animation="wave" />
        <CardContent>
          <Skeleton variant="text" width={260} height={20} />
        </CardContent>
      </Card>

      {/* Summary skeleton */}
      <Card>
        <Skeleton variant="rectangular" height={48} sx={{ borderRadius: 0 }} />
        <CardContent>
          <Box sx={{ display: 'flex', gap: 1.5, mb: 2.5 }}>
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} variant="rectangular" height={80} sx={{ flex: 1, borderRadius: 2 }} animation="wave" />
            ))}
          </Box>
          <Skeleton variant="text" width={120} height={18} sx={{ mb: 1 }} />
          <Box sx={{ display: 'flex', gap: 1 }}>
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} variant="rectangular" height={72} sx={{ flex: 1, borderRadius: 2 }} animation="wave" />
            ))}
          </Box>
        </CardContent>
      </Card>

      {/* ELD log skeleton (2 days) */}
      {[1, 2].map((d) => (
        <Card key={d}>
          <Skeleton variant="rectangular" height={52} sx={{ borderRadius: 0 }} animation="wave" />
          <CardContent>
            <Skeleton variant="text" width={340} height={16} sx={{ mb: 1.5 }} />
            <Skeleton
              variant="rectangular"
              height={212}
              animation="wave"
              sx={{ borderRadius: 1, mb: 2 }}
            />
            <Box sx={{ display: 'flex', gap: 1 }}>
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} variant="rectangular" height={64} sx={{ flex: 1, borderRadius: 1 }} animation="wave" />
              ))}
            </Box>
          </CardContent>
        </Card>
      ))}

      {/* Stop details skeleton */}
      <Card>
        <Skeleton variant="rectangular" height={48} sx={{ borderRadius: 0 }} />
        <CardContent sx={{ p: 0 }}>
          {[1, 2, 3, 4].map((i) => (
            <Box key={i} sx={{ px: 2.5, py: 2, display: 'flex', gap: 2, alignItems: 'flex-start' }}>
              <Skeleton variant="circular" width={36} height={36} animation="wave" />
              <Box sx={{ flex: 1 }}>
                <Skeleton variant="text" width={120} height={18} animation="wave" />
                <Skeleton variant="text" width={200} height={16} animation="wave" />
                <Skeleton variant="text" width={260} height={14} animation="wave" />
              </Box>
            </Box>
          ))}
        </CardContent>
      </Card>
    </Box>
  );
}
